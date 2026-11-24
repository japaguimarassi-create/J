import math
import random


class Expert:
    def __init__(self, width: int, seed: int, learning_rate: float = 1e-3):
        if width <= 0 or learning_rate <= 0:
            raise ValueError("Invalid expert configuration.")
        rng = random.Random(seed)
        self.width = width
        self.learning_rate = learning_rate
        self.weights = [[rng.uniform(-0.1, 0.1) for _ in range(width)] for _ in range(width)]
        self.bias = [0.0] * width
        self.steps = 0

    def forward(self, inputs: list[float]) -> list[float]:
        if len(inputs) != self.width:
            raise ValueError("Input width does not match expert width.")
        return [math.tanh(sum(w * x for w, x in zip(row, inputs)) + b) for row, b in zip(self.weights, self.bias)]

    def train_one(self, inputs: list[float], target: list[float]) -> float:
        if len(target) != self.width:
            raise ValueError("Target width does not match expert width.")
        output = self.forward(inputs)
        loss = sum((o - t) ** 2 for o, t in zip(output, target)) / self.width
        for i, (o, t) in enumerate(zip(output, target)):
            delta = 2.0 * (o - t) * (1.0 - o * o) / self.width
            for j, value in enumerate(inputs):
                self.weights[i][j] -= self.learning_rate * delta * value
            self.bias[i] -= self.learning_rate * delta
        self.steps += 1
        return loss


class ExpertRouter:
    def __init__(self, experts: list[Expert], top_k: int = 2):
        if not experts or not 1 <= top_k <= len(experts):
            raise ValueError("Invalid expert router configuration.")
        self.experts = experts
        self.top_k = top_k

    def route(self, inputs: list[float]) -> list[int]:
        ranked = sorted(
            range(len(self.experts)),
            key=lambda i: (sum(a * b for a, b in zip(inputs, self.experts[i].bias)), -i),
            reverse=True,
        )
        return ranked[:self.top_k]

    def forward(self, inputs: list[float]) -> list[float]:
        selected = self.route(inputs)
        outputs = [self.experts[i].forward(inputs) for i in selected]
        return [sum(row[j] for row in outputs) / len(outputs) for j in range(len(outputs[0]))]
