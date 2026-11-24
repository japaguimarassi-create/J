import argparse
import json
from pathlib import Path
import random

from .config import MatrixConfig
from .distributed import DistributedTrainer
from .experts import Expert
from .memory import MemoryBudget, VirtualWeightCache
from .scaling import CapacityPlan, estimate_runtime_bytes
from .sparse import SparseGraph
from .training import CombinedTrainer
from .virtual import VirtualMatrix


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="neural-matrix")
    parser.add_argument("--config", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inspect")
    sub.add_parser("plan")
    train = sub.add_parser("train")
    train.add_argument("--data", type=Path, required=True)
    train.add_argument("--checkpoint", type=Path, default=Path("checkpoints/latest.json"))
    train.add_argument("--mode", choices=("parallel", "incremental", "distributed"), default="parallel")
    train.add_argument("--workers", type=int)
    train.add_argument("--limit", type=int, default=100)
    return parser


def load_config(path: Path | None) -> MatrixConfig:
    if path is None:
        config = MatrixConfig()
    else:
        config = MatrixConfig(**json.loads(path.read_text(encoding="utf-8")))
    config.validate()
    return config


def load_dataset(path: Path, limit: int) -> list[tuple[list[float], list[float]]]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    dataset = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                inputs = list(map(float, item["x"]))
                target = list(map(float, item["y"]))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                raise ValueError(f"Invalid JSONL sample on line {line_number}: {error}") from error
            if not inputs or not target:
                raise ValueError(f"Input and target cannot be empty (line {line_number})")
            dataset.append((inputs, target))
            if len(dataset) >= limit:
                break
    return dataset


def _create_experts(config: MatrixConfig) -> list[Expert]:
    rng = random.Random(config.seed)
    return [Expert(config.expert_width, rng.randrange(1 << 30), config.learning_rate) for _ in range(config.expert_count)]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)

    if args.command == "inspect":
        virtual = VirtualMatrix(config.logical_units, config.logical_connections)
        graph = SparseGraph(config.active_units, config.active_edges, config.seed)
        graph.initialize(min(config.active_edges, config.active_units * 4))
        memory = MemoryBudget(config.virtual_cache_mb * 1024 * 1024)
        cache = VirtualWeightCache(virtual, memory)
        for row, column in virtual.sample_addresses(8, config.seed):
            cache.get(row, column)
        print(json.dumps({
            "version": "0.2.0",
            "logical_rows": config.logical_units,
            "logical_columns": config.logical_connections,
            "logical_addressable_entries": virtual.logical_connections,
            "active_units": config.active_units,
            "active_edges": len(graph.edges),
            "experts": config.expert_count,
            "top_k": config.top_k_experts,
            "estimated_runtime_bytes": estimate_runtime_bytes(
                config.active_units, config.active_edges, config.expert_count, config.expert_width,
                config.virtual_cache_mb * 1024 * 1024,
            ),
            "memory_limit_bytes": config.memory_limit_mb * 1024 * 1024,
            "virtual_cache_limit_bytes": config.virtual_cache_mb * 1024 * 1024,
            "virtual_weight_cache": memory.snapshot(),
            "workers_limit": config.max_workers,
        }, indent=2))
        return 0

    if args.command == "plan":
        print(json.dumps(CapacityPlan.from_config(config).to_dict(), indent=2))
        return 0

    if args.command == "train":
        dataset = load_dataset(args.data, args.limit)
        if not dataset:
            raise ValueError("Dataset is empty")
        for inputs, target in dataset:
            if len(inputs) != config.expert_width or len(target) != config.expert_width:
                raise ValueError(f"Every sample must have x and y width {config.expert_width}")
        experts = _create_experts(config)
        trainer = CombinedTrainer(experts, config.top_k_experts, config.max_workers)
        trainer.load_checkpoint(args.checkpoint)
        if args.mode == "parallel":
            loss = trainer.train_parallel(dataset)
            used_workers = min(trainer.workers, config.expert_count, len(dataset))
        elif args.mode == "incremental":
            losses = [trainer.train_incremental(sample) for sample in dataset]
            loss = sum(losses) / len(losses)
            used_workers = 1
        else:
            requested_workers = args.workers if args.workers is not None else config.max_workers
            distributed = DistributedTrainer(experts, requested_workers)
            distributed.stats = trainer.stats
            loss = distributed.train(dataset)
            trainer.stats = distributed.stats
            used_workers = distributed.workers
        trainer.save_checkpoint(args.checkpoint)
        print(json.dumps({
            "mode": args.mode,
            "workers": used_workers,
            "samples": len(dataset),
            "loss": loss,
            "checkpoint": str(args.checkpoint),
            "updates": trainer.stats.updates,
        }, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
