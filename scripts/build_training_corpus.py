import argparse
import json
import sys
import tempfile
from pathlib import Path

from deta.data import write_jsonl
from deta.github_catalog import GithubCatalog, GithubCatalogError


DEFAULT_REPOSITORIES = [
    "psf/requests",
    "pytest-dev/pytest",
    "pallets/flask",
    "pallets/werkzeug",
    "pallets/click",
    "pallets/jinja",
    "pallets/itsdangerous",
    "pallets/markupsafe",
    "pydantic/pydantic",
    "encode/httpx",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a bounded, license-screened code manifest from public GitHub repositories."
    )
    parser.add_argument("--output", default="data/approved.jsonl")
    parser.add_argument("--max-files-per-repo", type=int, default=12)
    parser.add_argument("--min-records", type=int, default=8)
    parser.add_argument("--repos", nargs="+", default=DEFAULT_REPOSITORIES)
    return parser


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
        delete=False,
    ) as stream:
        temporary_path = Path(stream.name)
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    temporary_path.replace(path)


def main() -> int:
    args = build_parser().parse_args()
    if not 1 <= args.max_files_per_repo <= 25:
        raise SystemExit("--max-files-per-repo must be between 1 and 25")
    if args.min_records < 1:
        raise SystemExit("--min-records must be positive")
    repositories = list(dict.fromkeys(args.repos))
    catalog = GithubCatalog()
    records = []
    report = []

    for repository in repositories:
        try:
            source_records = catalog.fetch_licensed_code(
                repository,
                max_files=args.max_files_per_repo,
            )
            records.extend(source_records)
            report.append({
                "repository": repository,
                "status": "accepted" if source_records else "no-eligible-files",
                "records": len(source_records),
            })
        except (GithubCatalogError, ValueError) as exc:
            report.append({
                "repository": repository,
                "status": "skipped",
                "records": 0,
                "reason": str(exc),
            })

    destination = Path(args.output)
    written = write_jsonl(iter(records), destination)
    summary = {
        "candidate_repositories": len(repositories),
        "records_before_deduplication": len(records),
        "records_written": written,
        "output": str(destination),
        "policy": "approved-license allowlist; file-level SPDX checks; secret-pattern exclusion; SHA-256 provenance; exact-content deduplication",
        "sources": report,
    }
    report_path = destination.with_suffix(".report.json")
    write_json_atomic(report_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if written < args.min_records:
        print(
            f"Only {written} eligible unique records were collected; at least {args.min_records} are required.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
