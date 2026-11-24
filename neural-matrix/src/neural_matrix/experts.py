import math
import random


def validate_vector(values: list[float], width: int, label: str) -> list[float]:
    if not isinstance(values, list) or len(values) != width:
        raise ValueError(f"{label} width must be {width}")
    normalized = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{label} values must be finite numbers")
        number = float(value)
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
        loss = sum((actual - desired) ** 2 for actual, desired in zip(output, expected)) / self.width
        for row_index, (actual, desired) in enumerate(zip(output, expected)):
            delta = 2.0 * (actual - desired) * (1.0 - actual * actual) / self.width
            for column_index, value in enumerate(values):
                self.weights[row_index][column_index] -= self.learning_rate * delta * value
            self.bias[row_index] -= self.learning_rate * delta
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
