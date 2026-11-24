import math


class RegressionMetrics:
    def __init__(self):
        self.samples = 0
        self.values = 0
        self._squared_error = 0.0
        self._absolute_error = 0.0

    def update(self, prediction: list[float], target: list[float]) -> None:
        if not isinstance(prediction, list) or not isinstance(target, list):
            raise ValueError("Prediction and target must be vectors")
        if not prediction or len(prediction) != len(target):
            raise ValueError("Prediction and target must have the same non-zero width")
        for actual, expected in zip(prediction, target):
            if isinstance(actual, bool) or isinstance(expected, bool):
                raise ValueError("Metric values must be finite numbers")
            if not isinstance(actual, (int, float)) or not isinstance(expected, (int, float)):
                raise ValueError("Metric values must be finite numbers")
            if not math.isfinite(actual) or not math.isfinite(expected):
                raise ValueError("Metric values must be finite numbers")
            difference = float(actual) - float(expected)
            self._squared_error += difference * difference
            self._absolute_error += abs(difference)
            self.values += 1
        self.samples += 1

    def to_dict(self) -> dict[str, float | int | None]:
        if self.values == 0:
            return {"samples": 0, "values": 0, "mse": None, "mae": None}
        return {
            "samples": self.samples,
            "values": self.values,
            "mse": self._squared_error / self.values,
            "mae": self._absolute_error / self.values,
        }
