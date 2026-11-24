from collections.abc import Iterable, Iterator
import json
import math
from pathlib import Path


Sample = tuple[list[float], list[float]]


def _read_vector(value: object, width: int, line_number: int, field: str) -> list[float]:
    if not isinstance(value, list):
        raise ValueError(f"Invalid {field} vector on line {line_number}: expected a JSON array")
    if len(value) != width:
        raise ValueError(
            f"Invalid {field} width on line {line_number}: expected {width}, received {len(value)}"
        )
    result: list[float] = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"Invalid {field}[{index}] on line {line_number}: expected a finite number")
        number = float(item)
        if not math.isfinite(number):
            raise ValueError(f"Invalid {field}[{index}] on line {line_number}: expected a finite number")
        result.append(number)
    return result


def iter_jsonl(
    path: str | Path,
    input_width: int,
    target_width: int,
    limit: int | None = None,
) -> Iterator[Sample]:
    if input_width <= 0 or target_width <= 0:
        raise ValueError("input_width and target_width must be positive")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")

    seen = 0
    with Path(path).open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if limit is not None and seen >= limit:
                break
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on line {line_number}: {error.msg}") from error
            if not isinstance(item, dict):
                raise ValueError(f"Invalid record on line {line_number}: expected a JSON object")
            if "x" not in item or "y" not in item:
                raise ValueError(f"Invalid record on line {line_number}: expected x and y arrays")
            inputs = _read_vector(item["x"], input_width, line_number, "x")
            target = _read_vector(item["y"], target_width, line_number, "y")
            yield inputs, target
            seen += 1


def iter_batches(samples: Iterable[Sample], batch_size: int) -> Iterator[list[Sample]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    batch: list[Sample] = []
    for sample in samples:
        batch.append(sample)
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
