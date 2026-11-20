import argparse
import json
import re
from pathlib import Path


ALLOWED_LICENSES = {
    "0bsd", "apache-2.0", "bsd-2-clause", "bsd-3-clause",
    "cc0-1.0", "isc", "mit", "unlicense", "zlib",
}
TARGET_LANGUAGES = {
    "c": "c", "c#": "csharp", "c-sharp": "csharp",
    "c++": "cpp", "cpp": "cpp", "css": "css", "html": "html",
    "java": "java", "javascript": "javascript", "js": "javascript",
    "lua": "lua", "python": "python", "sql": "sql",
    "typescript": "typescript", "ts": "typescript", "go": "go",
    "rust": "rust", "ruby": "ruby", "php": "php", "shell": "shell",
    "bash": "shell", "kotlin": "kotlin", "swift": "swift",
    "scala": "scala", "perl": "perl", "r": "r", "julia": "julia",
    "dart": "dart", "powershell": "powershell",
    "visual-basic": "visual_basic", "fortran": "fortran",
    "haskell": "haskell", "dockerfile": "dockerfile",
    "cmake": "cmake", "makefile": "makefile", "assembly": "assembly",
    "batchfile": "batchfile",
}
LICENSE_FIELDS = ("licenses", "license", "repository_license", "max_stars_repo_licenses")
LANGUAGE_FIELDS = ("lang", "language")
REPOSITORY_FIELDS = ("repository_name", "repo_name", "max_stars_repo_name")
PATH_FIELDS = ("path", "repository_path", "max_stars_repo_path")
COMMIT_FIELDS = ("commit_hash", "hexsha", "max_stars_repo_head_hexsha")
SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def first_present(row, fields):
    for field in fields:
        value = row.get(field)
        if value not in (None, "", [], {}):
            return value
    return None


def license_values(value):
    if value is None:
        return []
    if isinstance(value, dict):
        values = list(value.keys()) + list(value.values())
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        raw = str(value).strip()
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, (list, tuple, set)):
                values = list(decoded)
            elif isinstance(decoded, dict):
                values = list(decoded.keys()) + list(decoded.values())
            else:
                values = [decoded]
        except json.JSONDecodeError:
            values = re.split(r"[,;|]", raw)
    normalized = []
    for item in values:
        candidates = item.values() if isinstance(item, dict) else (item,)
        for candidate in candidates:
            text = str(candidate or "").strip().lower()
            text = text.removeprefix("spdx:").replace(" ", "")
            if text:
                normalized.append(text)
    return sorted(set(normalized))


def scan_secrets(content):
    return any(pattern.search(content) for pattern in SECRET_PATTERNS)


def prepare(args):
    import pyarrow.parquet as parquet

    args.output.parent.mkdir(parents=True, exist_ok=True)
    counts = {language: 0 for language in set(TARGET_LANGUAGES.values())}
    seen = set()
    kept = 0
    skipped = {"license": 0, "language": 0, "content": 0, "secret_pattern": 0, "duplicate": 0}
    with args.output.open("w", encoding="utf-8") as output:
        for parquet_path in sorted(args.input.rglob("*.parquet")):
            parquet_file = parquet.ParquetFile(parquet_path)
            columns = set(parquet_file.schema.names)
            if "content" not in columns:
                raise ValueError(f"Missing content column in {parquet_path}")
            if not any(field in columns for field in LICENSE_FIELDS):
                raise ValueError(f"No recognized license field in {parquet_path}; expected one of {LICENSE_FIELDS}")
            if not any(field in columns for field in LANGUAGE_FIELDS):
                raise ValueError(f"No language field in {parquet_path}; expected one of {LANGUAGE_FIELDS}")
            selected_fields = (
                "content", *LICENSE_FIELDS, *LANGUAGE_FIELDS,
                *REPOSITORY_FIELDS, *PATH_FIELDS, *COMMIT_FIELDS,
            )
            selected = [field for field in selected_fields if field in columns]
            for batch in parquet_file.iter_batches(batch_size=256, columns=selected):
                for row in batch.to_pylist():
                    raw_licenses = license_values(first_present(row, LICENSE_FIELDS))
                    accepted_licenses = sorted(set(raw_licenses) & ALLOWED_LICENSES)
                    if not accepted_licenses:
                        skipped["license"] += 1
                        continue
                    raw_language = str(first_present(row, LANGUAGE_FIELDS) or "").strip().lower()
                    language = TARGET_LANGUAGES.get(raw_language)
                    if language is None or counts[language] >= args.max_per_language:
                        skipped["language"] += 1
                        continue
                    content = str(row.get("content") or "").replace("\r\n", "\n").replace("\r", "\n")
                    if len(content) < args.min_chars or len(content) > args.max_chars:
                        skipped["content"] += 1
                        continue
                    if scan_secrets(content):
                        skipped["secret_pattern"] += 1
                        continue
                    digest_key = (raw_language, content)
                    if digest_key in seen:
                        skipped["duplicate"] += 1
                        continue
                    seen.add(digest_key)
                    record = {
                        "text": f"<|language|>{language}\n<|code|>\n{content}",
                        "language": "en",
                        "kind": "code",
                        "source": "bigcode/the-stack-v1.3",
                        "licenses": accepted_licenses,
                        "repository": first_present(row, REPOSITORY_FIELDS),
                        "path": first_present(row, PATH_FIELDS),
                        "commit_hash": first_present(row, COMMIT_FIELDS),
                    }
                    output.write(json.dumps(record, ensure_ascii=False) + "\n")
                    counts[language] += 1
                    kept += 1
                if all(value >= args.max_per_language for value in counts.values()):
                    break
            if all(value >= args.max_per_language for value in counts.values()):
                break

    report = {
        "dataset": "bigcode/the-stack v1.3",
        "source_schema_fields": {
            "content": "content",
            "language_candidates": list(LANGUAGE_FIELDS),
            "license_candidates": list(LICENSE_FIELDS),
        },
        "allowed_spdx_ids": sorted(ALLOWED_LICENSES),
        "records_kept": kept,
        "per_language": counts,
        "skipped": skipped,
        "output": str(args.output),
        "note": "The Stack v1 is gated. The user must personally review and accept its current Terms of Use before download. Preserve original licenses and provenance. The Stack v2 is not supported by this importer.",
    }
    report_path = args.output.with_suffix(args.output.suffix + ".manifest.json")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="Local directory containing authorized The Stack v1.3 Parquet shards")
    parser.add_argument("--output", type=Path, default=Path("corpus/stack_filtered.jsonl"))
    parser.add_argument("--max-per-language", type=int, default=15000)
    parser.add_argument("--min-chars", type=int, default=120)
    parser.add_argument("--max-chars", type=int, default=30000)
    args = parser.parse_args()
    if not args.input.is_dir():
        parser.error("input must be an existing directory")
    if args.max_per_language < 1 or args.min_chars < 1 or args.max_chars < args.min_chars:
        parser.error("invalid filtering limits")
    prepare(args)


if __name__ == "__main__":
    main()
