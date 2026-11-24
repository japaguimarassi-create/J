from dataclasses import asdict
from pathlib import Path
import random

from .checkpoint import read_checkpoint, write_checkpoint
from .config import MatrixConfig
from .distributed import DistributedTrainer
from .experts import Expert
from .memory import MemoryBudget, VirtualWeightCache
from .scaling import CapacityPlan
from .sparse import SparseGraph
from .training import CombinedTrainer
from .virtual import VirtualMatrix


class NeuralMatrixModel:
    architecture = "expert-mlp-tanh-v1"

    def __init__(self, config: MatrixConfig | None = None):
        self.config = config or MatrixConfig()
        self.config.validate()
        CapacityPlan.from_config(self.config)
        rng = random.Random(self.config.seed)
        self.experts = [
            Expert(self.config.expert_width, rng.randrange(1 << 30), self.config.learning_rate)
            for _ in range(self.config.expert_count)
        ]
        self.trainer = CombinedTrainer(
            self.experts,
            top_k=self.config.top_k_experts,
            workers=self.config.max_workers,
        )
        self.router = self.trainer.router
        self.sparse_graph = SparseGraph(
            self.config.active_units, self.config.active_edges, self.config.seed
        )
        self.sparse_graph.initialize(
            min(self.config.active_edges, self.config.active_units * 4)
        )
        self.virtual_matrix = VirtualMatrix(
            self.config.logical_units, self.config.logical_connections
        )
        self.memory_budget = MemoryBudget(self.config.virtual_cache_mb * 1024 * 1024)
        self.virtual_weights = VirtualWeightCache(self.virtual_matrix, self.memory_budget)

    @property
    def stats(self):
        return self.trainer.stats

    def predict(self, inputs: list[float]) -> list[float]:
        return self.router.forward(inputs)

    def train_sample(self, sample: tuple[list[float], list[float]]) -> float:
        if not isinstance(sample, (tuple, list)) or len(sample) != 2:
            raise ValueError("A sample must contain input and target vectors")
        return self.trainer.train_incremental((sample[0], sample[1]))

    def train_batch(
        self,
        samples: list[tuple[list[float], list[float]]],
        mode: str = "parallel",
        workers: int | None = None,
    ) -> float:
        if mode not in ("incremental", "parallel", "distributed"):
            raise ValueError("mode must be incremental, parallel, or distributed")
        validated = []
        for sample in samples:
            if not isinstance(sample, (tuple, list)) or len(sample) != 2:
                raise ValueError("Each sample must contain input and target vectors")
            inputs, target = sample
            self.router.route(inputs)
            if not isinstance(target, list) or len(target) != self.config.expert_width:
                raise ValueError(f"Target width must be {self.config.expert_width}")
            normalized_target = []
            for value in target:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError("Target values must be finite numbers")
                number = float(value)
                if number != number or number in (float("inf"), float("-inf")):
                    raise ValueError("Target values must be finite numbers")
                normalized_target.append(number)
            validated.append((list(map(float, inputs)), normalized_target))
        if not validated:
            return 0.0

        requested_workers = self.config.max_workers if workers is None else int(workers)
        if requested_workers <= 0:
            raise ValueError("workers must be positive")
        effective_workers = min(requested_workers, self.config.max_workers, len(self.experts))
        if mode == "incremental":
            losses = [self.trainer.train_incremental(sample) for sample in validated]
            return sum(losses) / len(losses)
        if mode == "parallel":
            self.trainer.workers = effective_workers
            return self.trainer.train_parallel(validated)

        distributed = DistributedTrainer(
            self.experts,
            workers=effective_workers,
            top_k=self.config.top_k_experts,
        )
        distributed.stats = self.trainer.stats
        return distributed.train(validated)

    def save(self, path: str | Path) -> None:
        payload = self.trainer.state_dict()
        payload.update({
            "format_version": 2,
            "architecture": self.architecture,
            "config": asdict(self.config),
        })
        write_checkpoint(path, payload)

    def load(self, path: str | Path) -> "NeuralMatrixModel":
        payload = read_checkpoint(path)
        architecture = payload.get("architecture")
        if architecture not in (None, self.architecture):
            raise ValueError("Checkpoint architecture does not match this model")
        saved_config = payload.get("config")
        if saved_config is not None:
            if not isinstance(saved_config, dict):
                raise ValueError("Checkpoint config must be an object")
            try:
                restored_config = MatrixConfig(**saved_config)
                restored_config.validate()
            except (TypeError, ValueError) as error:
                raise ValueError(f"Checkpoint configuration is invalid: {error}") from error
            if restored_config != self.config:
                raise ValueError("Checkpoint configuration does not match this model")
        self.trainer.load_state_dict(payload)
        return self

    @classmethod
    def from_checkpoint(cls, path: str | Path) -> "NeuralMatrixModel":
        payload = read_checkpoint(path)
        saved_config = payload.get("config")
        if saved_config is not None:
            if not isinstance(saved_config, dict):
                raise ValueError("Checkpoint config must be an object")
            try:
                config = MatrixConfig(**saved_config)
            except TypeError as error:
                raise ValueError(f"Checkpoint configuration is invalid: {error}") from error
        else:
            saved_experts = payload.get("experts")
            if not isinstance(saved_experts, list) or not saved_experts:
                raise ValueError("Legacy checkpoint has no expert state")
            width = payload.get("expert_width")
            if not isinstance(width, int) or width <= 0:
                weights = saved_experts[0].get("weights")
                width = len(weights) if isinstance(weights, list) else 0
            config = MatrixConfig(
                expert_count=len(saved_experts),
                expert_width=width,
                top_k_experts=min(2, len(saved_experts)),
            )
        model = cls(config)
        model.load(path)
        return model
