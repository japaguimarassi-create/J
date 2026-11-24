import argparse
import json
from pathlib import Path
import sys

from .config import MatrixConfig
from .data import iter_batches, iter_jsonl
from .evaluation import evaluate
from .memory import MemoryBudget, VirtualWeightCache
from .model import NeuralMatrixModel
from .scaling import CapacityPlan, estimate_runtime_bytes
from .sparse import SparseGraph
from .synthetic import write_synthetic_jsonl
from .virtual import VirtualMatrix


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="neural-matrix")
    parser.add_argument("--config", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inspect")
    sub.add_parser("plan")

    generate = sub.add_parser("generate")
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--samples", type=int, default=256)
    generate.add_argument("--width", type=int, default=32)
    generate.add_argument("--seed", type=int, default=17)

    train = sub.add_parser("train")
    train.add_argument("--data", type=Path, required=True)
    train.add_argument("--checkpoint", type=Path, default=Path("checkpoints/latest.json"))
    train.add_argument("--mode", choices=("incremental", "parallel", "distributed"), default="incremental")
    train.add_argument("--workers", type=int)
    train.add_argument("--limit", type=int)
    train.add_argument("--epochs", type=int, default=1)
    train.add_argument("--batch-size", type=int, default=16)

    predict = sub.add_parser("predict")
    predict.add_argument("--checkpoint", type=Path, required=True)
    predict.add_argument("--input", required=True, help="JSON array of numeric input values")

    evaluate_command = sub.add_parser("evaluate")
    evaluate_command.add_argument("--checkpoint", type=Path, required=True)
    evaluate_command.add_argument("--data", type=Path, required=True)
    evaluate_command.add_argument("--limit", type=int)

    return parser


def load_config(path: Path | None) -> MatrixConfig:
    if path is None:
        config = MatrixConfig()
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Configuration root must be a JSON object")
        config = MatrixConfig(**payload)
    config.validate()
    return config


def _model_for_training(args) -> tuple[NeuralMatrixModel, bool]:
    resumed = args.checkpoint.exists()
    if resumed and args.config is None:
        return NeuralMatrixModel.from_checkpoint(args.checkpoint), True
    model = NeuralMatrixModel(load_config(args.config))
    if resumed:
        model.load(args.checkpoint)
    return model, resumed


def _run_generate(args) -> dict:
    if args.samples <= 0:
        raise ValueError("samples must be positive")
    if args.width <= 0:
        raise ValueError("width must be positive")
    count = write_synthetic_jsonl(
        args.output,
        samples=args.samples,
        width=args.width,
        seed=args.seed,
    )
    return {
        "output": str(args.output),
        "samples": count,
        "width": args.width,
        "seed": args.seed,
    }


def _run_train(args) -> dict:
    if args.epochs <= 0:
        raise ValueError("epochs must be positive")
    if args.batch_size <= 0:
        raise ValueError("batch-size must be positive")
    if args.limit is not None and args.limit <= 0:
        raise ValueError("limit must be positive")
    if args.workers is not None and args.workers <= 0:
        raise ValueError("workers must be positive")

    model, resumed = _model_for_training(args)
    samples_seen = 0
    weighted_loss = 0.0
    for _ in range(args.epochs):
        epoch_samples = 0
        epoch_loss = 0.0
        stream = iter_jsonl(
            args.data,
            model.config.expert_width,
            model.config.expert_width,
            limit=args.limit,
        )
        for batch in iter_batches(stream, args.batch_size):
            loss = model.train_batch(batch, mode=args.mode, workers=args.workers)
            epoch_samples += len(batch)
            epoch_loss += loss * len(batch)
        if epoch_samples == 0:
            raise ValueError("Training dataset is empty")
        samples_seen += epoch_samples
        weighted_loss += epoch_loss
        model.save(args.checkpoint)

    return {
        "mode": args.mode,
        "epochs": args.epochs,
        "samples": samples_seen,
        "mean_loss": weighted_loss / samples_seen,
        "updates": model.stats.updates,
        "checkpoint": str(args.checkpoint),
        "resumed": resumed,
    }


def _run_predict(args) -> dict:
    try:
        inputs = json.loads(args.input)
    except json.JSONDecodeError as error:
        raise ValueError(f"--input must be a JSON array: {error.msg}") from error
    model = NeuralMatrixModel.from_checkpoint(args.checkpoint)
    prediction = model.predict(inputs)
    return {"prediction": prediction, "checkpoint": str(args.checkpoint)}


def _run_evaluate(args) -> dict:
    if args.limit is not None and args.limit <= 0:
        raise ValueError("limit must be positive")
    model = NeuralMatrixModel.from_checkpoint(args.checkpoint)
    samples = iter_jsonl(
        args.data,
        model.config.expert_width,
        model.config.expert_width,
        limit=args.limit,
    )
    result = evaluate(model, samples)
    result["checkpoint"] = str(args.checkpoint)
    return result


def _run_inspect(config: MatrixConfig) -> dict:
    virtual = VirtualMatrix(config.logical_units, config.logical_connections)
    memory = MemoryBudget(config.virtual_cache_mb * 1024 * 1024)
    cache = VirtualWeightCache(virtual, memory)
    graph = SparseGraph(config.active_units, config.active_edges, config.seed)
    graph.initialize_virtual(
        virtual,
        min(config.active_edges, config.active_units * 4),
        seed=config.seed,
        weight_getter=cache.get,
    )
    return {
        "version": "0.3.0",
        "logical_rows": config.logical_units,
        "logical_columns": config.logical_connections,
        "logical_addressable_entries": virtual.logical_connections,
        "active_units": config.active_units,
        "active_edges": len(graph.edges),
        "experts": config.expert_count,
        "top_k": config.top_k_experts,
        "estimated_runtime_bytes": estimate_runtime_bytes(
            config.active_units,
            config.active_edges,
            config.expert_count,
            config.expert_width,
            config.virtual_cache_mb * 1024 * 1024,
        ),
        "memory_limit_bytes": config.memory_limit_mb * 1024 * 1024,
        "virtual_cache_limit_bytes": config.virtual_cache_mb * 1024 * 1024,
        "virtual_weight_cache": memory.snapshot(),
        "workers_limit": config.max_workers,
    }


def run(args) -> dict:
    if args.command in ("inspect", "plan"):
        config = load_config(args.config)
        if args.command == "inspect":
            return _run_inspect(config)
        return CapacityPlan.from_config(config).to_dict()
    if args.command == "generate":
        return _run_generate(args)
    if args.command == "train":
        return _run_train(args)
    if args.command == "predict":
        return _run_predict(args)
    if args.command == "evaluate":
        return _run_evaluate(args)
    raise ValueError(f"Unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run(args)
    except (OSError, ValueError, TypeError, MemoryError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
