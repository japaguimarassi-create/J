import argparse
import gzip
import hashlib
import json
import os
import random
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
            if not isinstance(row, dict):
                raise ValueError(f"Source {source_name} line {line_number} must be a JSON object.")
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


def allocate_quotas(total, active_sources, weights):
    weight_total = sum(weights[name] for name in active_sources)
    exact = {
        name: total * weights[name] / weight_total
        for name in active_sources
    }
    quotas = {name: int(value) for name, value in exact.items()}
    remainder = total - sum(quotas.values())
    order = sorted(
        active_sources,
        key=lambda name: exact[name] - quotas[name],
        reverse=True,
    )
    for name in order[:remainder]:
        quotas[name] += 1
    return quotas


def mix_corpora(sources, weights, output_path, max_records=0, require_license=False, seed=2026):
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
    duplicates = {name: 0 for name in sources}
    missing_license = {name: 0 for name in sources}
    active = {
        name: iter(source_rows(path, name))
        for name, path in sources.items()
    }
    rng = random.Random(seed)
    seen_count = 0
    total_written = 0

    with tempfile.TemporaryDirectory(prefix="hypercode-mix-") as temp_dir:
        database = sqlite3.connect(str(Path(temp_dir) / "seen.sqlite"))
        database.execute("CREATE TABLE seen (digest TEXT PRIMARY KEY)")
        source_temp_paths = {
            name: Path(temp_dir) / f"{name}.jsonl"
            for name in sources
        }
        source_outputs = {
            name: source_temp_paths[name].open("w", encoding="utf-8")
            for name in sources
        }
        try:
            while active and (max_records == 0 or total_written < max_records):
                if max_records:
                    quotas = allocate_quotas(
                        max_records - total_written,
                        list(active),
                        normalized_weights,
                    )
                else:
                    quotas = {name: None for name in active}

                for name in list(active):
                    quota = quotas[name]
                    accepted = 0
                    while quota is None or accepted < quota:
                        try:
                            row = next(active[name])
                        except StopIteration:
                            del active[name]
                            break

                        if require_license and not row["license"]:
                            missing_license[name] += 1
                            continue

                        digest = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
                        cursor = database.execute(
                            "INSERT OR IGNORE INTO seen(digest) VALUES (?)",
                            (digest,),
                        )
                        if cursor.rowcount == 0:
                            duplicates[name] += 1
                            continue

                        row["sha256"] = digest
                        row["source_record_id"] = row["source_record_id"] or digest
                        source_outputs[name].write(
                            json.dumps(row, ensure_ascii=False) + "\n"
                        )
                        counts[name] += 1
                        seen_count += 1
                        accepted += 1
                        total_written += 1
                        if total_written % 10000 == 0:
                            database.commit()
                        if max_records and total_written >= max_records:
                            break
                    if max_records and total_written >= max_records:
                        break

                if max_records and total_written >= max_records:
                    break
        finally:
            for handle in source_outputs.values():
                handle.close()
            database.commit()
            database.close()

        if total_written == 0:
            raise ValueError("No usable unique records were written. Check paths, source fields and license filters.")

        opener = gzip.open if str(destination).endswith(".gz") else open
        with opener(temporary_output, "wt", encoding="utf-8") as output:
            source_order = list(sources)
            rng.shuffle(source_order)
            for name in source_order:
                with source_temp_paths[name].open("r", encoding="utf-8") as source_file:
                    for line in source_file:
                        output.write(line)

    os.replace(temporary_output, destination)
    total_weight = sum(counts.values())
    report = {
        "output": str(destination),
        "records_written": total_written,
        "unique_records_written": seen_count,
        "source_weights": normalized_weights,
        "source_counts": counts,
        "source_actual_mix": {
            name: count / total_weight if total_weight else 0.0
            for name, count in counts.items()
        },
        "duplicates": duplicates,
        "missing_license": missing_license,
        "require_license_metadata": require_license,
        "max_records": max_records,
        "near_duplicate_deduplication": False,
        "note": "Input shards should be shuffled before mixing. Verify source terms and licenses; provenance remains attached to every record.",
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
    parser.add_argument("--seed", type=int, default=2026)
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
        seed=args.seed,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
