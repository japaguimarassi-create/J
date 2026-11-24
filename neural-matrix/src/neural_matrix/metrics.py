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

        sample_squared_error = 0.0
        sample_absolute_error = 0.0
        for actual, expected in zip(prediction, target):
            if isinstance(actual, bool) or isinstance(expected, bool):
                raise ValueError("Metric values must be finite numbers")
            if not isinstance(actual, (int, float)) or not isinstance(expected, (int, float)):
                raise ValueError("Metric values must be finite numbers")
            try:
                actual_value = float(actual)
                expected_value = float(expected)
            except OverflowError as error:
                raise ValueError("Metric values must be finite numbers") from error
            if not math.isfinite(actual_value) or not math.isfinite(expected_value):
                raise ValueError("Metric values must be finite numbers")
            difference = actual_value - expected_value
            squared_error = difference * difference
            if not math.isfinite(difference) or not math.isfinite(squared_error):
                raise ValueError("Metric accumulation overflowed")
            sample_squared_error += squared_error
            sample_absolute_error += abs(difference)
            if not math.isfinite(sample_squared_error) or not math.isfinite(sample_absolute_error):
                raise ValueError("Metric accumulation overflowed")

        next_squared_error = self._squared_error + sample_squared_error
        next_absolute_error = self._absolute_error + sample_absolute_error
        if not math.isfinite(next_squared_error) or not math.isfinite(next_absolute_error):
            raise ValueError("Metric accumulation overflowed")
        self._squared_error = next_squared_error
        self._absolute_error = next_absolute_error
        self.values += len(prediction)
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
