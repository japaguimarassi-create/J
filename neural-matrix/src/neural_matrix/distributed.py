from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
import os

from .experts import Expert, ExpertRouter, validate_vector
from .training import TrainingStats


def _train_expert_shard(payload: tuple) -> tuple:
    width, learning_rate, weights, bias, steps, samples = payload
    expert = Expert(width, seed=0, learning_rate=learning_rate)
    expert.weights = weights
    expert.bias = bias
    expert.steps = steps
    total_loss = 0.0
    for inputs, target in samples:
        total_loss += expert.train_one(inputs, target)
    return expert.weights, expert.bias, expert.steps, len(samples), total_loss


class DistributedTrainer:
    """Parallelizes independent expert shards across local Python worker processes."""

    def __init__(self, experts: list[Expert], workers: int | None = None, top_k: int = 1):
        if not experts:
            raise ValueError("At least one expert is required")
        available = os.cpu_count() or 1
        requested = available if workers is None else int(workers)
        if requested <= 0:
            raise ValueError("workers must be positive")
        self.experts = experts
        self.router = ExpertRouter(experts, top_k)
        self.workers = min(requested, available, len(experts))
        self.stats = TrainingStats()

    def train(self, dataset: list[tuple[list[float], list[float]]]) -> float:
        if not dataset:
            return 0.0
        buckets = [[] for _ in self.experts]
        for inputs, target in dataset:
            values = validate_vector(inputs, self.router.width, "Input")
            expected = validate_vector(target, self.router.width, "Target")
            for index in self.router.route(values):
                buckets[index].append((values, expected))

        payloads = []
        indices = []
        for index, (expert, samples) in enumerate(zip(self.experts, buckets)):
            if not samples:
                continue
            payloads.append((expert.width, expert.learning_rate, expert.weights, expert.bias, expert.steps, samples))
            indices.append(index)
        if self.workers == 1 or len(payloads) == 1:
            results = [_train_expert_shard(payload) for payload in payloads]
        else:
            with ProcessPoolExecutor(max_workers=min(self.workers, len(payloads)), mp_context=get_context("spawn")) as pool:
                results = list(pool.map(_train_expert_shard, payloads))

        updates = 0
        total_loss = 0.0
        for index, result in zip(indices, results):
            weights, bias, steps, expert_updates, loss_sum = result
            expert = self.experts[index]
            expert.weights = weights
            expert.bias = bias
            expert.steps = steps
            updates += expert_updates
            total_loss += loss_sum
        mean_loss = total_loss / max(1, updates)
        sample_count = len(dataset)
        self.stats.samples += sample_count
        self.stats.updates += updates
        self.stats.mean_loss += (mean_loss - self.stats.mean_loss) * sample_count / self.stats.samples
        return mean_loss
