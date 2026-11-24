from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
import json
import math
import os
import tempfile

from .experts import Expert, ExpertRouter


@dataclass
class TrainingStats:
    samples: int = 0
    updates: int = 0
    mean_loss: float = 0.0


class CombinedTrainer:
    def __init__(self, experts: list[Expert], top_k: int = 2, workers: int | None = None):
        self.experts = experts
        self.router = ExpertRouter(experts, top_k)
        self.workers = min(workers if workers is not None else 4, len(experts))
        if self.workers <= 0:
            raise ValueError("workers must be positive")
        self.stats = TrainingStats()

    def train_incremental(self, sample: tuple[list[float], list[float]]) -> float:
        inputs, target = sample
        selected = self.router.route(inputs)
        losses = [self.experts[i].train_one(inputs, target) for i in selected]
        loss = sum(losses) / len(losses)
        self.stats.samples += 1
        self.stats.updates += len(selected)
        self.stats.mean_loss += (loss - self.stats.mean_loss) / self.stats.samples
        return loss

    def train_parallel(self, dataset: list[tuple[list[float], list[float]]]) -> float:
        if not dataset:
            return 0.0
        buckets = [[] for _ in self.experts]
        for index, sample in enumerate(dataset):
            buckets[index % len(buckets)].append(sample)

        def train_bucket(args):
            expert, samples = args
            total = 0.0
            for inputs, target in samples:
                total += expert.train_one(inputs, target)
            return len(samples), total

        active = [(expert, bucket) for expert, bucket in zip(self.experts, buckets) if bucket]
        with ThreadPoolExecutor(max_workers=min(self.workers, len(active))) as pool:
            results = list(pool.map(train_bucket, active))
        count = sum(item[0] for item in results)
        loss = sum(item[1] for item in results) / max(1, count)
        self.stats.samples += count
        self.stats.updates += count
        self.stats.mean_loss += (loss - self.stats.mean_loss) * count / self.stats.samples
        return loss

    def save_checkpoint(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "format_version": 1,
            "expert_width": self.experts[0].width,
            "stats": vars(self.stats),
            "experts": [{"weights": e.weights, "bias": e.bias, "steps": e.steps} for e in self.experts],
        }
        fd, temporary = tempfile.mkstemp(prefix=path.name, dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(state, stream, separators=(",", ":"), allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def load_checkpoint(self, path: str | Path) -> bool:
        path = Path(path)
        if not path.exists():
            return False
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("format_version", 0) not in (0, 1):
            raise ValueError("Unsupported checkpoint format")
        saved_experts = state.get("experts")
        if not isinstance(saved_experts, list) or len(saved_experts) != len(self.experts):
            raise ValueError("Checkpoint expert count mismatch.")
        if state.get("expert_width", self.experts[0].width) != self.experts[0].width:
            raise ValueError("Checkpoint expert width mismatch")
        validated = []
        for expert, saved in zip(self.experts, saved_experts):
            weights = saved.get("weights")
            bias = saved.get("bias")
            steps = saved.get("steps")
            if not isinstance(weights, list) or len(weights) != expert.width:
                raise ValueError("Checkpoint dimensions mismatch.")
            if any(not isinstance(row, list) or len(row) != expert.width for row in weights):
                raise ValueError("Checkpoint dimensions mismatch.")
            if not isinstance(bias, list) or len(bias) != expert.width:
                raise ValueError("Checkpoint bias dimensions mismatch")
            values = [value for row in weights for value in row] + bias
            if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in values):
                raise ValueError("Checkpoint contains invalid numeric values")
            if not isinstance(steps, int) or steps < 0:
                raise ValueError("Checkpoint step count is invalid")
            validated.append((weights, bias, steps))
        stats = state.get("stats", {})
        loaded_stats = TrainingStats(
            samples=int(stats.get("samples", 0)),
            updates=int(stats.get("updates", 0)),
            mean_loss=float(stats.get("mean_loss", 0.0)),
        )
        if loaded_stats.samples < 0 or loaded_stats.updates < 0 or not math.isfinite(loaded_stats.mean_loss):
            raise ValueError("Checkpoint statistics are invalid")
        for expert, (weights, bias, steps) in zip(self.experts, validated):
            expert.weights = weights
            expert.bias = bias
            expert.steps = steps
        self.stats = loaded_stats
        return True
