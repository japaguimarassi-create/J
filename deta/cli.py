import argparse
import json
from pathlib import Path

import torch

from deta import __version__
from deta.assistant import DetaAssistant
from deta.config import DetaConfig
from deta.data import read_licensed_jsonl, write_jsonl
from deta.github_catalog import GithubCatalog
from deta.knowledge import KnowledgeStore
from deta.model import build_default_model, build_grouped_model
from deta.projects import create_project
from deta.training import DEFAULT_MAX_TRAINING_BYTES, train_checkpoint, train_five_groups
from deta.web import read_web_page, search_web
from deta.verification import (
    DEFAULT_MAX_PROJECT_BYTES,
    DEFAULT_MAX_PROJECT_FILES,
    collect_project_files,
    run_pytest_in_current_project,
    verify_bundle,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="deta", description="Deta experimental AI foundation")
    parser.add_argument("--version", action="version", version=f"deta {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor", help="Check the Python and grouped-model runtime")
    commands.add_parser("count-params", help="Print the exact parameter count for the 400k model")

    search = commands.add_parser("search-github", help="Search public GitHub repositories")
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=5)

    ingest = commands.add_parser("ingest-github", help="Ingest code from one license-approved public repository")
    ingest.add_argument("--repo", required=True)
    ingest.add_argument("--max-files", type=int, default=10)
    ingest.add_argument("--output", required=True)

    train = commands.add_parser("train", help="Train the 400k model one 80k group at a time")
    train.add_argument("--data", required=True)
    train.add_argument("--output-dir", default="checkpoints/deta-400k")
    train.add_argument("--steps-per-group", type=int, default=1000)
    train.add_argument("--start-group", type=int, default=1)
    train.add_argument("--end-group", type=int, default=5)
    train.add_argument("--device", choices=["cpu", "cuda"], default=None)
    train.add_argument("--resume-from", default=None)
    train.add_argument("--seed", type=int, default=42)
    train.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_TRAINING_BYTES)

    baseline = commands.add_parser("train-baseline", help="Train the original 79,824-parameter reference baseline")
    baseline.add_argument("--data", required=True)
    baseline.add_argument("--output", required=True)
    baseline.add_argument("--steps", type=int, default=1000)
    baseline.add_argument("--device", choices=["cpu", "cuda"], default=None)
    baseline.add_argument("--resume-from", default=None)
    baseline.add_argument("--seed", type=int, default=42)
    baseline.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_TRAINING_BYTES)

    verify = commands.add_parser("verify", help="Run the four verification gates over a source project")
    verify.add_argument("--project", default=".")
    verify.add_argument("--references", default=None, help="Optional JSONL manifest of licensed code references")
    verify.add_argument("--run-tests", action="store_true", help="Explicitly run pytest for this trusted project")
    verify.add_argument("--max-files", type=int, default=DEFAULT_MAX_PROJECT_FILES)
    verify.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_PROJECT_BYTES)

    ask = commands.add_parser("ask", help="Answer using public internet retrieval and the local knowledge index")
    ask.add_argument("question", nargs="+")
    ask.add_argument("--offline", action="store_true", help="Use only the local knowledge index")
    ask.add_argument("--results", type=int, default=5)
    ask.add_argument("--read-pages", type=int, default=3)

    web_search = commands.add_parser("web-search", help="Search the public web without an AI API key")
    web_search.add_argument("query", nargs="+")
    web_search.add_argument("--limit", type=int, default=5)

    read_url = commands.add_parser("read-url", help="Read and extract text from a public HTTPS page")
    read_url.add_argument("url")
    read_url.add_argument("--max-chars", type=int, default=20000)

    knowledge = commands.add_parser("knowledge", help="Inspect or search the local knowledge index")
    knowledge.add_argument("--query", default=None)
    knowledge.add_argument("--limit", type=int, default=8)

    clear_knowledge = commands.add_parser("clear-knowledge", help="Clear the local knowledge index")
    clear_knowledge.add_argument("--yes", action="store_true", help="Confirm removal of all indexed documents")

    project = commands.add_parser("create-project", help="Generate a local game, social prototype, or Python tool")
    project.add_argument("--kind", required=True, choices=["browser-game", "social-app", "python-cli"])
    project.add_argument("--name", required=True)
    project.add_argument("--output", required=True)
    project.add_argument("--brief", default="")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "ask":
        result = DetaAssistant().ask(
            " ".join(args.question),
            web=not args.offline,
            max_results=args.results,
            pages_to_read=args.read_pages,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "web-search":
        print(json.dumps(search_web(" ".join(args.query), limit=args.limit), ensure_ascii=False, indent=2))
        return

    if args.command == "read-url":
        page = read_web_page(args.url, max_chars=args.max_chars)
        print(json.dumps(page, ensure_ascii=False, indent=2))
        return

    if args.command == "knowledge":
        store = KnowledgeStore()
        if args.query:
            print(json.dumps(store.search(args.query, limit=args.limit), ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"documents": store.count(), "path": str(store.path)}, ensure_ascii=False, indent=2))
        return

    if args.command == "clear-knowledge":
        if not args.yes:
            parser.error("Pass --yes to confirm clearing the local knowledge index.")
        print(json.dumps({"removed_documents": KnowledgeStore().clear()}, indent=2))
        return

    if args.command == "create-project":
        result = create_project(args.kind, args.name, args.output, args.brief)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "doctor":
        config = DetaConfig()
        config.validate()
        model = build_grouped_model(config)
        baseline = build_default_model()
        print(json.dumps({
            "version": __version__,
            "python_model_runtime": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "target_parameters": config.target_parameters,
            "actual_trainable_parameters": model.parameter_count(),
            "parameters_per_group": [model.group_parameter_count(i) for i in range(model.group_count)],
            "baseline_parameters": baseline.parameter_count(),
            "conceptual_action_units": config.conceptual_action_units,
            "training_groups": config.groups,
            "apk_created": False,
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "count-params":
        config = DetaConfig()
        model = build_grouped_model(config)
        baseline = build_default_model()
        print(json.dumps({
            "target_parameters": config.target_parameters,
            "actual_trainable_parameters": model.parameter_count(),
            "parameters_per_group": [model.group_parameter_count(i) for i in range(model.group_count)],
            "baseline_parameters": baseline.parameter_count(),
            "conceptual_action_units": config.conceptual_action_units,
            "group_count": model.group_count,
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
        result = train_five_groups(
            data_path=args.data,
            output_dir=args.output_dir,
            steps_per_group=args.steps_per_group,
            start_group=args.start_group,
            end_group=args.end_group,
            device=args.device,
            resume_from=args.resume_from,
            seed=args.seed,
            max_bytes=args.max_bytes,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "train-baseline":
        result = train_checkpoint(
            data_path=args.data,
            output_path=args.output,
            steps=args.steps,
            device=args.device,
            resume_from=args.resume_from,
            seed=args.seed,
            max_bytes=args.max_bytes,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "verify":
        project_root = Path(args.project).expanduser().resolve()
        try:
            files = collect_project_files(
                project_root,
                max_files=args.max_files,
                max_bytes=args.max_bytes,
            )
            references = list(read_licensed_jsonl(args.references)) if args.references else []
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
            return
        test_runner = (lambda: run_pytest_in_current_project(project_root)) if args.run_tests else None
        report = verify_bundle(files, references=references, test_runner=test_runner)
        payload = {
            "project": str(project_root),
            "files_scanned": len(files),
            "passed": report.passed,
            "checks": [
                {"name": check.name, "passed": check.passed, "details": check.details}
                for check in report.checks
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        if not report.passed:
            raise SystemExit(1)
        return

    parser.error("Unknown command")


if __name__ == "__main__":
    main()
