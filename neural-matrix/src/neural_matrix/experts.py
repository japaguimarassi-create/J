import math
import random


def validate_vector(values: list[float], width: int, label: str) -> list[float]:
    if not isinstance(values, list) or len(values) != width:
        raise ValueError(f"{label} width must be {width}")
    normalized = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{label} values must be finite numbers")
        try:
            number = float(value)
        except OverflowError as error:
            raise ValueError(f"{label} values must be finite numbers") from error
        if not math.isfinite(number):
            raise ValueError(f"{label} values must be finite numbers")
        normalized.append(number)
    return normalized


class Expert:
    def __init__(self, width: int, seed: int, learning_rate: float = 1e-3):
        if width <= 0 or not math.isfinite(learning_rate) or learning_rate <= 0:
            raise ValueError("Invalid expert configuration.")
        rng = random.Random(seed)
        self.width = width
        self.learning_rate = float(learning_rate)
        self.weights = [[rng.uniform(-0.1, 0.1) for _ in range(width)] for _ in range(width)]
        self.bias = [0.0] * width
        self.steps = 0

    def forward(self, inputs: list[float]) -> list[float]:
        values = validate_vector(inputs, self.width, "Input")
        return [
            math.tanh(sum(weight * value for weight, value in zip(row, values)) + bias)
            for row, bias in zip(self.weights, self.bias)
        ]

    def train_one(self, inputs: list[float], target: list[float]) -> float:
        values = validate_vector(inputs, self.width, "Input")
        expected = validate_vector(target, self.width, "Target")
        output = self.forward(values)

        squared_errors = []
        for actual, desired in zip(output, expected):
            difference = actual - desired
            squared_error = difference * difference
            if not math.isfinite(difference) or not math.isfinite(squared_error):
                raise ValueError("Training loss overflowed for the supplied sample")
            squared_errors.append(squared_error)
        loss = sum(squared_errors) / self.width
        if not math.isfinite(loss):
            raise ValueError("Training loss overflowed for the supplied sample")

        new_weights = []
        new_bias = []
        for row_index, (actual, desired) in enumerate(zip(output, expected)):
            delta = 2.0 * (actual - desired) * (1.0 - actual * actual) / self.width
            if not math.isfinite(delta):
                raise ValueError("Training gradient overflowed for the supplied sample")
            row = []
            for column_index, value in enumerate(values):
                updated = self.weights[row_index][column_index] - self.learning_rate * delta * value
                if not math.isfinite(updated):
                    raise ValueError("Training weight update overflowed for the supplied sample")
                row.append(updated)
            updated_bias = self.bias[row_index] - self.learning_rate * delta
            if not math.isfinite(updated_bias):
                raise ValueError("Training bias update overflowed for the supplied sample")
            new_weights.append(row)
            new_bias.append(updated_bias)

        self.weights = new_weights
        self.bias = new_bias
        self.steps += 1
        return loss


class ExpertRouter:
    def __init__(self, experts: list[Expert], top_k: int = 2):
        if not experts or not 1 <= top_k <= len(experts):
            raise ValueError("Invalid expert router configuration.")
        widths = {expert.width for expert in experts}
        if len(widths) != 1:
            raise ValueError("All experts must have the same width")
        self.experts = experts
        self.top_k = top_k
        self.width = experts[0].width

    def route(self, inputs: list[float]) -> list[int]:
        values = validate_vector(inputs, self.width, "Input")

        def score(index: int) -> tuple[float, int]:
            expert = self.experts[index]
            projection = sum(value * weight for value, weight in zip(values, expert.weights[0]))
            bias_signal = sum(value * bias for value, bias in zip(values, expert.bias))
            return projection + bias_signal, -index

        ranked = sorted(range(len(self.experts)), key=score, reverse=True)
        return ranked[:self.top_k]

    def forward(self, inputs: list[float]) -> list[float]:
        selected = self.route(inputs)
        outputs = [self.experts[index].forward(inputs) for index in selected]
        return [
            sum(output[index] for output in outputs) / len(outputs)
            for index in range(self.width)
        ]
