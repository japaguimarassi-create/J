from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
import math
from pathlib import Path

from .checkpoint import read_checkpoint, write_checkpoint
from .experts import Expert, ExpertRouter, validate_vector


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
        values = validate_vector(inputs, self.router.width, "Input")
        expected = validate_vector(target, self.router.width, "Target")
        selected = self.router.route(values)
        losses = [self.experts[index].train_one(values, expected) for index in selected]
        loss = sum(losses) / len(losses)
        self.stats.samples += 1
        self.stats.updates += len(selected)
        self.stats.mean_loss += (loss - self.stats.mean_loss) / self.stats.samples
        return loss

    def train_parallel(self, dataset: list[tuple[list[float], list[float]]]) -> float:
        if not dataset:
            return 0.0
        buckets = [[] for _ in self.experts]
        for inputs, target in dataset:
            values = validate_vector(inputs, self.router.width, "Input")
            expected = validate_vector(target, self.router.width, "Target")
            for index in self.router.route(values):
                buckets[index].append((values, expected))

        def train_bucket(args):
            expert, samples = args
            total = 0.0
            for inputs, target in samples:
                total += expert.train_one(inputs, target)
            return len(samples), total

        active = [(expert, bucket) for expert, bucket in zip(self.experts, buckets) if bucket]
        with ThreadPoolExecutor(max_workers=min(self.workers, len(active))) as pool:
            results = list(pool.map(train_bucket, active))
        updates = sum(item[0] for item in results)
        loss = sum(item[1] for item in results) / max(1, updates)
        sample_count = len(dataset)
        self.stats.samples += sample_count
        self.stats.updates += updates
        self.stats.mean_loss += (loss - self.stats.mean_loss) * sample_count / self.stats.samples
        return loss

    def state_dict(self) -> dict:
        return {
            "format_version": 1,
            "expert_width": self.router.width,
            "stats": asdict(self.stats),
            "experts": [
                {"weights": expert.weights, "bias": expert.bias, "steps": expert.steps}
                for expert in self.experts
            ],
        }

    def load_state_dict(self, state: dict) -> None:
        if not isinstance(state, dict):
            raise ValueError("Checkpoint must be an object")
        version = state.get("format_version", 0)
        if version not in (0, 1, 2):
            raise ValueError("Unsupported checkpoint format")
        architecture = state.get("architecture")
        if architecture not in (None, "expert-mlp-tanh-v1"):
            raise ValueError("Unsupported model architecture")
        saved_experts = state.get("experts")
        if not isinstance(saved_experts, list) or len(saved_experts) != len(self.experts):
            raise ValueError("Checkpoint expert count mismatch.")
        if state.get("expert_width", self.router.width) != self.router.width:
            raise ValueError("Checkpoint expert width mismatch")

        validated = []
        for expert, saved in zip(self.experts, saved_experts):
            if not isinstance(saved, dict):
                raise ValueError("Checkpoint expert entry must be an object")
            weights = saved.get("weights")
            bias = saved.get("bias")
            steps = saved.get("steps")
            if not isinstance(weights, list) or len(weights) != expert.width:
                raise ValueError("Checkpoint weight dimensions mismatch")
            normalized_weights = []
            for row in weights:
                if not isinstance(row, list) or len(row) != expert.width:
                    raise ValueError("Checkpoint weight dimensions mismatch")
                normalized_row = []
                for value in row:
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                        raise ValueError("Checkpoint contains invalid weight values")
                    normalized_row.append(float(value))
                normalized_weights.append(normalized_row)
            if not isinstance(bias, list) or len(bias) != expert.width:
                raise ValueError("Checkpoint bias dimensions mismatch")
            normalized_bias = []
            for value in bias:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError("Checkpoint contains invalid bias values")
                normalized_bias.append(float(value))
            if isinstance(steps, bool) or not isinstance(steps, int) or steps < 0:
                raise ValueError("Checkpoint step count is invalid")
            validated.append((normalized_weights, normalized_bias, steps))

        stats = state.get("stats", {})
        if not isinstance(stats, dict):
            raise ValueError("Checkpoint statistics must be an object")
        samples = stats.get("samples", 0)
        updates = stats.get("updates", 0)
        mean_loss = stats.get("mean_loss", 0.0)
        if isinstance(samples, bool) or not isinstance(samples, int) or samples < 0:
            raise ValueError("Checkpoint sample count is invalid")
        if isinstance(updates, bool) or not isinstance(updates, int) or updates < 0:
            raise ValueError("Checkpoint update count is invalid")
        if isinstance(mean_loss, bool) or not isinstance(mean_loss, (int, float)) or not math.isfinite(mean_loss):
            raise ValueError("Checkpoint mean loss is invalid")

        for expert, (weights, bias, steps) in zip(self.experts, validated):
            expert.weights = weights
            expert.bias = bias
            expert.steps = steps
        self.stats = TrainingStats(samples=samples, updates=updates, mean_loss=float(mean_loss))

    def save_checkpoint(self, path: str | Path) -> None:
        write_checkpoint(path, self.state_dict())

    def load_checkpoint(self, path: str | Path) -> bool:
        checkpoint_path = Path(path)
        if not checkpoint_path.exists():
            return False
        self.load_state_dict(read_checkpoint(checkpoint_path))
        return True
