import argparse
import gzip
import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path

from tokenizer import normalize_text


def parse_assignments(values, kind):
    parsed = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"{kind} entries must use NAME=VALUE.")
        name, raw = value.split("=", 1)
        name = name.strip()
        raw = raw.strip()
        if not name or not raw:
            raise ValueError(f"Invalid {kind} entry: {value}")
        if name in parsed:
            raise ValueError(f"Duplicate {kind} name: {name}")
        parsed[name] = raw
    return parsed


def source_rows(path, source_name):
    source = Path(path)
    opener = gzip.open if str(source).endswith(".gz") else open
    with opener(source, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON in source {source_name} at line {line_number}: {error}"
                ) from error
            raw_text = row.get("text") or row.get("content") or row.get("document")
            if not isinstance(raw_text, str) or not raw_text.strip():
                continue
            text = normalize_text(raw_text)
            if not text.strip():
                continue
            yield {
                "text": text,
                "source": source_name,
                "repository": row.get("repository") or row.get("repo_name"),
                "language": row.get("language") or row.get("lang"),
                "kind": row.get("kind") or row.get("type") or source_name,
                "license": row.get("license") or row.get("licenses"),
                "source_record_id": row.get("id") or row.get("path") or row.get("url"),
            }


def mix_corpora(sources, weights, output_path, max_records=0, require_license=False):
    if not sources:
        raise ValueError("At least one --source NAME=PATH is required.")
    if max_records < 0:
        raise ValueError("max_records cannot be negative.")
    if set(weights) - set(sources):
        raise ValueError("A weight was provided for a source that does not exist.")
    normalized_weights = {
        name: float(weights.get(name, 1.0)) for name in sources
    }
    if any(value <= 0 for value in normalized_weights.values()):
        raise ValueError("All source weights must be positive.")

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = destination.with_suffix(destination.suffix + ".tmp")
    counts = {name: 0 for name in sources}
    skipped = {name: 0 for name in sources}
    seen_count = 0
    total_written = 0
    active = {
        name: iter(source_rows(path, name))
        for name, path in sources.items()
    }
    current = {name: 0.0 for name in sources}

    with tempfile.TemporaryDirectory(prefix="hypercode-dedup-") as temp_dir:
        database = sqlite3.connect(str(Path(temp_dir) / "seen.sqlite"))
        database.execute("CREATE TABLE seen (digest TEXT PRIMARY KEY)")
        opener = gzip.open if str(destination).endswith(".gz") else open
        try:
            with opener(temporary_output, "wt", encoding="utf-8") as output:
                while active and (max_records == 0 or total_written < max_records):
                    active_weight = sum(normalized_weights[name] for name in active)
                    for name in active:
                        current[name] += normalized_weights[name]
                    selected = max(active, key=lambda name: current[name])
                    current[selected] -= active_weight
                    try:
                        row = next(active[selected])
                    except StopIteration:
                        del active[selected]
                        continue

                    digest = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
                    cursor = database.execute(
                        "INSERT OR IGNORE INTO seen(digest) VALUES (?)",
                        (digest,),
                    )
                    if cursor.rowcount == 0:
                        skipped[selected] += 1
                        continue

                    seen_count += 1
                    if require_license and not row["license"]:
                        skipped[selected] += 1
                        continue

                    row["sha256"] = digest
                    output.write(json.dumps(row, ensure_ascii=False) + "\n")
                    counts[selected] += 1
                    total_written += 1
                    if total_written % 10000 == 0:
                        database.commit()
        finally:
            database.commit()
            database.close()

    os.replace(temporary_output, destination)
    total_weight = sum(counts.values())
    report = {
        "output": str(destination),
        "records_written": total_written,
        "unique_records_seen": seen_count,
        "require_license_metadata": require_license,
        "source_weights": normalized_weights,
        "source_counts": counts,
        "source_actual_mix": {
            name: count / total_weight if total_weight else 0.0
            for name, count in counts.items()
        },
        "duplicates_or_filtered": skipped,
        "near_duplicate_deduplication": False,
        "note": "Verify source terms and license compatibility before training; provenance is preserved per record.",
    }
    report_path = destination.with_suffix(destination.suffix + ".report.json")
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--weight", action="append", default=[], metavar="NAME=WEIGHT")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-records", type=int, default=0)
    parser.add_argument("--require-license-metadata", action="store_true")
    args = parser.parse_args()
    sources = parse_assignments(args.source, "source")
    raw_weights = parse_assignments(args.weight, "weight")
    weights = {name: float(value) for name, value in raw_weights.items()}
    report = mix_corpora(
        sources,
        weights,
        args.output,
        max_records=args.max_records,
        require_license=args.require_license_metadata,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
