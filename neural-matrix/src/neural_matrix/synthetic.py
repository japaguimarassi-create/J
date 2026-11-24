import json
import math
from pathlib import Path
import random
from collections.abc import Iterator


def _validate_dimensions(samples: int, width: int) -> None:
    if isinstance(samples, bool) or not isinstance(samples, int) or samples <= 0:
        raise ValueError("samples must be a positive integer")
    if isinstance(width, bool) or not isinstance(width, int) or width <= 0:
        raise ValueError("width must be a positive integer")


def iter_synthetic(samples: int = 256, width: int = 32, seed: int = 17) -> Iterator[tuple[list[float], list[float]]]:
    _validate_dimensions(samples, width)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    teacher = [
        [rng.uniform(-0.75, 0.75) for _ in range(width)]
        for _ in range(width)
    ]
    scale = math.sqrt(width)
    for _ in range(samples):
        inputs = [rng.uniform(-1.0, 1.0) for _ in range(width)]
        target = [
            math.tanh(sum(weight * value for weight, value in zip(row, inputs)) / scale)
            for row in teacher
        ]
        yield inputs, target


def write_synthetic_jsonl(
    path: str | Path,
    samples: int = 256,
    width: int = 32,
    seed: int = 17,
    create_parent: bool = True,
) -> int:
    _validate_dimensions(samples, width)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    output = Path(path)
    if create_parent:
        output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8") as stream:
        for inputs, target in iter_synthetic(samples, width, seed):
            stream.write(json.dumps({"x": inputs, "y": target}, separators=(",", ":"), allow_nan=False))
            stream.write("\n")
            count += 1
    return count
