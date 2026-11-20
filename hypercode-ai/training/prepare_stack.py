import argparse
import json
import re
from pathlib import Path

import pyarrow.parquet as parquet


ALLOWED_LICENSES = {
    "0bsd", "apache-2.0", "bsd-2-clause", "bsd-3-clause",
    "cc0-1.0", "isc", "mit", "unlicense", "zlib",
}
TARGET_LANGUAGES = {
    "c#": "csharp", "c++": "cpp", "c": "c", "css": "css",
    "html": "html", "java": "java", "javascript": "javascript",
    "lua": "lua", "python": "python", "sql": "sql",
    "typescript": "typescript",
}
SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]"
)


def normalize_license(value):
    return str(value or "").strip().lower().replace(" ", "")


def prepare(args):
    args.output.parent.mkdir(parents=True, exist_ok=True)
    counts = {language: 0 for language in TARGET_LANGUAGES.values()}
    seen = set()
    kept = 0
    skipped = {"license": 0, "language": 0, "content": 0, "secret_pattern": 0, "duplicate": 0}
    with args.output.open("w", encoding="utf-8") as output:
        for parquet_path in sorted(args.input.rglob("*.parquet")):
            parquet_file = parquet.ParquetFile(parquet_path)
            columns = set(parquet_file.schema.names)
            required = {"content", "license"}
            if not required.issubset(columns):
                raise ValueError(f"Missing columns {sorted(required - columns)} in {parquet_path}")
            selected = [
                column for column in ("content", "license", "language", "repo_name", "path", "commit_hash")
                if column in columns
            ]
            for batch in parquet_file.iter_batches(batch_size=256, columns=selected):
                for row in batch.to_pylist():
                    license_id = normalize_license(row.get("license"))
                    if license_id not in ALLOWED_LICENSES:
                        skipped["license"] += 1
                        continue
                    raw_language = str(row.get("language") or "").strip().lower()
                    language = TARGET_LANGUAGES.get(raw_language)
                    if language is None or counts[language] >= args.max_per_language:
                        skipped["language"] += 1
                        continue
                    content = str(row.get("content") or "").replace("\r\n", "\n").replace("\r", "\n")
                    if len(content) < args.min_chars or len(content) > args.max_chars:
                        skipped["content"] += 1
                        continue
                    if SECRET_PATTERN.search(content):
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
                        "source": "bigcode/the-stack",
                        "license": row.get("license"),
                        "repository": row.get("repo_name"),
                        "path": row.get("path"),
                        "commit_hash": row.get("commit_hash"),
                    }
                    output.write(json.dumps(record, ensure_ascii=False) + "\n")
                    counts[language] += 1
                    kept += 1
                if all(value >= args.max_per_language for value in counts.values()):
                    break

    report = {
        "dataset": "bigcode/the-stack",
        "allowed_spdx_ids": sorted(ALLOWED_LICENSES),
        "records_kept": kept,
        "per_language": counts,
        "skipped": skipped,
        "output": str(args.output),
        "note": "Keep original repository license notices and provenance metadata with downstream use. Review the current dataset access terms before downloading or training.",
    }
    report_path = args.output.with_suffix(args.output.suffix + ".manifest.json")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="Local directory containing downloaded The Stack Parquet files")
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
