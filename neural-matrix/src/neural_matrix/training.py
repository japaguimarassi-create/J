from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
import json
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
        self.workers = workers or min(4, len(experts))
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

        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            results = list(pool.map(train_bucket, [(e, b) for e, b in zip(self.experts, buckets) if b]))
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
            "stats": vars(self.stats),
            "experts": [{"weights": e.weights, "bias": e.bias, "steps": e.steps} for e in self.experts],
        }
        fd, temporary = tempfile.mkstemp(prefix=path.name, dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(state, stream, separators=(",", ":"))
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
        if len(state["experts"]) != len(self.experts):
            raise ValueError("Checkpoint expert count mismatch.")
        for expert, saved in zip(self.experts, state["experts"]):
            if len(saved["weights"]) != expert.width or any(len(row) != expert.width for row in saved["weights"]):
                raise ValueError("Checkpoint dimensions mismatch.")
            expert.weights = saved["weights"]
            expert.bias = saved["bias"]
            expert.steps = saved["steps"]
        self.stats = TrainingStats(**state["stats"])
        return True
