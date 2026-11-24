import argparse
import json
from pathlib import Path
import random

from .config import MatrixConfig
from .experts import Expert
from .sparse import SparseGraph
from .training import CombinedTrainer
from .virtual import VirtualMatrix


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="neural-matrix")
    parser.add_argument("--config", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inspect")
    train = sub.add_parser("train")
    train.add_argument("--data", type=Path, required=True)
    train.add_argument("--checkpoint", type=Path, default=Path("checkpoints/latest.json"))
    train.add_argument("--mode", choices=("parallel", "incremental"), default="parallel")
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
        for line in stream:
            if not line.strip():
                continue
            item = json.loads(line)
            dataset.append((list(map(float, item["x"])), list(map(float, item["y"]))))
            if len(dataset) >= limit:
                break
    return dataset


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)

    if args.command == "inspect":
        virtual = VirtualMatrix(config.logical_units, config.logical_connections)
        graph = SparseGraph(config.active_units, config.active_edges, config.seed)
        graph.initialize(min(config.active_edges, config.active_units * 4))
        print(json.dumps({
            "version": "0.1.0",
            "logical_units": config.logical_units,
            "logical_connections": config.logical_connections,
            "logical_address_space": virtual.logical_connections,
            "active_units": config.active_units,
            "active_edges": len(graph.edges),
            "experts": config.expert_count,
            "top_k": config.top_k_experts,
        }, indent=2))
        return 0

    if args.command == "train":
        dataset = load_dataset(args.data, args.limit)
        if not dataset:
            raise ValueError("Dataset is empty")
        rng = random.Random(config.seed)
        experts = [Expert(config.expert_width, rng.randrange(1 << 30), config.learning_rate) for _ in range(config.expert_count)]
        trainer = CombinedTrainer(experts, config.top_k_experts)
        trainer.load_checkpoint(args.checkpoint)
        if args.mode == "parallel":
            loss = trainer.train_parallel(dataset)
        else:
            losses = [trainer.train_incremental(sample) for sample in dataset]
            loss = sum(losses) / len(losses)
        trainer.save_checkpoint(args.checkpoint)
        print(json.dumps({"samples": len(dataset), "loss": loss, "checkpoint": str(args.checkpoint), "updates": trainer.stats.updates}, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
