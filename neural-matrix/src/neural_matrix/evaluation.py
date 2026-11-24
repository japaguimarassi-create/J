from collections.abc import Iterable

from .metrics import RegressionMetrics


def evaluate(model, samples: Iterable[tuple[list[float], list[float]]], limit: int | None = None) -> dict:
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    metrics = RegressionMetrics()
    for sample in samples:
        if limit is not None and metrics.samples >= limit:
            break
        if not isinstance(sample, (tuple, list)) or len(sample) != 2:
            raise ValueError("Each dataset sample must contain input and target vectors")
        inputs, target = sample
        prediction = model.predict(inputs)
        metrics.update(prediction, target)
    result = metrics.to_dict()
    if result["samples"] == 0:
        raise ValueError("Cannot evaluate an empty dataset")
    return result
