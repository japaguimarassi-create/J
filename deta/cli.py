import argparse
import json
from pathlib import Path

import torch

from deta import __version__
from deta.config import DetaConfig
from deta.data import write_jsonl
from deta.github_catalog import GithubCatalog
from deta.model import build_default_model
from deta.training import train_checkpoint


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="deta", description="Deta experimental AI foundation")
    parser.add_argument("--version", action="version", version=f"deta {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor", help="Check the Python and model runtime")
    commands.add_parser("count-params", help="Print the actual trainable parameter count")

    search = commands.add_parser("search-github", help="Search public GitHub repositories")
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=5)

    ingest = commands.add_parser("ingest-github", help="Ingest code from one license-approved public repository")
    ingest.add_argument("--repo", required=True)
    ingest.add_argument("--max-files", type=int, default=10)
    ingest.add_argument("--output", required=True)

    train = commands.add_parser("train", help="Train the small byte-level baseline from licensed JSONL records")
    train.add_argument("--data", required=True)
    train.add_argument("--output", required=True)
    train.add_argument("--steps", type=int, default=1000)
    train.add_argument("--device", choices=["cpu", "cuda"], default=None)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "doctor":
        config = DetaConfig()
        config.validate()
        model = build_default_model()
        print(json.dumps({
            "version": __version__,
            "python_model_runtime": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "target_parameters": config.target_parameters,
            "conceptual_action_units": config.conceptual_action_units,
            "actual_trainable_parameters": model.parameter_count(),
            "apk_created": False,
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "count-params":
        model = build_default_model()
        print(json.dumps({
            "target_parameters": DetaConfig().target_parameters,
            "actual_trainable_parameters": model.parameter_count(),
            "conceptual_action_units": DetaConfig().conceptual_action_units,
            "is_general_intelligence": False,
        }, indent=2))
        return

    if args.command == "search-github":
        results = GithubCatalog().search_repositories(args.query, args.limit)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    if args.command == "ingest-github":
        records = GithubCatalog().fetch_licensed_code(args.repo, args.max_files)
        count = write_jsonl(iter(records), args.output)
        print(json.dumps({
            "repository": args.repo,
            "records_written": count,
            "output": str(Path(args.output)),
            "apk_created": False,
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "train":
        result = train_checkpoint(args.data, args.output, args.steps, device=args.device)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    parser.error("Unknown command")


if __name__ == "__main__":
    main()
