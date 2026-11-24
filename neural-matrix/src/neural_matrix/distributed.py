from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
import os

from .experts import Expert
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
    """Parallelizes independent expert shards across local worker processes."""

    def __init__(self, experts: list[Expert], workers: int | None = None):
        if not experts:
            raise ValueError("At least one expert is required")
        available = os.cpu_count() or 1
        requested = available if workers is None else int(workers)
        if requested <= 0:
            raise ValueError("workers must be positive")
        self.experts = experts
        self.workers = min(requested, available, len(experts))
        self.stats = TrainingStats()

    def train(self, dataset: list[tuple[list[float], list[float]]]) -> float:
        if not dataset:
            return 0.0
        buckets = [[] for _ in self.experts]
        for index, sample in enumerate(dataset):
            buckets[index % len(buckets)].append(sample)
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
            with ProcessPoolExecutor(max_workers=self.workers, mp_context=get_context("spawn")) as pool:
                results = list(pool.map(_train_expert_shard, payloads))
        count = 0
        total_loss = 0.0
        for index, result in zip(indices, results):
            weights, bias, steps, samples, loss_sum = result
            expert = self.experts[index]
            expert.weights = weights
            expert.bias = bias
            expert.steps = steps
            count += samples
            total_loss += loss_sum
        mean_loss = total_loss / max(1, count)
        self.stats.samples += count
        self.stats.updates += count
        self.stats.mean_loss += (mean_loss - self.stats.mean_loss) * count / self.stats.samples
        return mean_loss
