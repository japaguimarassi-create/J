from dataclasses import dataclass
import random
from typing import Iterable


@dataclass(frozen=True)
class Edge:
    source: int
    target: int
    weight: float


class SparseGraph:
    def __init__(self, unit_count: int, max_edges: int, seed: int = 17):
        if unit_count <= 0 or max_edges < 0:
            raise ValueError("Invalid sparse graph limits.")
        self.unit_count = unit_count
        self.max_edges = max_edges
        self._edges: list[Edge] = []
        self._rng = random.Random(seed)

    @property
    def edges(self) -> tuple[Edge, ...]:
        return tuple(self._edges)

    def add_edge(self, source: int, target: int, weight: float) -> None:
        if not 0 <= source < self.unit_count or not 0 <= target < self.unit_count:
            raise IndexError("Node index outside active graph.")
        if len(self._edges) >= self.max_edges:
            raise RuntimeError("Sparse graph active-edge budget reached.")
        self._edges.append(Edge(source, target, float(weight)))

    def initialize(self, count: int) -> None:
        if count < 0 or count > self.max_edges:
            raise ValueError("Requested edge count exceeds graph budget.")
        for _ in range(count):
            self.add_edge(
                self._rng.randrange(self.unit_count),
                self._rng.randrange(self.unit_count),
                self._rng.uniform(-0.1, 0.1),
            )

    def aggregate(self, values: Iterable[float]) -> list[float]:
        values = list(values)
        if len(values) != self.unit_count:
            raise ValueError("Input length must equal active unit count.")
        output = [0.0] * self.unit_count
        for edge in self._edges:
            output[edge.target] += values[edge.source] * edge.weight
        return output
