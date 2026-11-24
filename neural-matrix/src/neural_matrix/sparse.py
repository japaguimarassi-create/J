from dataclasses import dataclass
import math
import random
from typing import Callable, Iterable

from .virtual import VirtualMatrix


@dataclass(frozen=True)
class Edge:
    source: int
    target: int
    weight: float


class SparseGraph:
    def __init__(self, unit_count: int, max_edges: int, seed: int = 17):
        if isinstance(unit_count, bool) or not isinstance(unit_count, int):
            raise ValueError("unit_count must be an integer")
        if isinstance(max_edges, bool) or not isinstance(max_edges, int):
            raise ValueError("max_edges must be an integer")
        if unit_count <= 0 or max_edges < 0:
            raise ValueError("Invalid sparse graph limits.")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")
        self.unit_count = unit_count
        self.max_edges = max_edges
        self._edges: list[Edge] = []
        self._rng = random.Random(seed)

    @property
    def edges(self) -> tuple[Edge, ...]:
        return tuple(self._edges)

    def add_edge(self, source: int, target: int, weight: float) -> None:
        if isinstance(source, bool) or not isinstance(source, int):
            raise ValueError("Edge source must be an integer")
        if isinstance(target, bool) or not isinstance(target, int):
            raise ValueError("Edge target must be an integer")
        if not 0 <= source < self.unit_count or not 0 <= target < self.unit_count:
            raise IndexError("Node index outside active graph.")
        if len(self._edges) >= self.max_edges:
            raise RuntimeError("Sparse graph active-edge budget reached.")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise ValueError("Edge weight must be a finite number")
        try:
            normalized_weight = float(weight)
        except OverflowError as error:
            raise ValueError("Edge weight must be a finite number") from error
        if not math.isfinite(normalized_weight):
            raise ValueError("Edge weight must be a finite number")
        self._edges.append(Edge(source, target, normalized_weight))

    def initialize(self, count: int) -> None:
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError("count must be an integer")
        if count < 0 or count > self.max_edges:
            raise ValueError("Requested edge count exceeds graph budget.")
        for _ in range(count):
            self.add_edge(
                self._rng.randrange(self.unit_count),
                self._rng.randrange(self.unit_count),
                self._rng.uniform(-0.1, 0.1),
            )

    def initialize_virtual(
        self,
        matrix: VirtualMatrix,
        count: int,
        seed: int = 17,
        weight_getter: Callable[[int, int], float] | None = None,
    ) -> None:
        if self._edges:
            raise RuntimeError("Sparse graph is already initialized")
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError("count must be an integer")
        if count < 0 or count > self.max_edges:
            raise ValueError("Requested edge count exceeds graph budget")
        addresses = matrix.sample_addresses(count, seed)
        get_weight = weight_getter or matrix.deterministic_weight
        for row, column in addresses:
            self.add_edge(
                row % self.unit_count,
                column % self.unit_count,
                get_weight(row, column),
            )

    def aggregate(self, values: Iterable[float]) -> list[float]:
        values = list(values)
        if len(values) != self.unit_count:
            raise ValueError("Input length must equal active unit count.")
        output = [0.0] * self.unit_count
        for edge in self._edges:
            output[edge.target] += values[edge.source] * edge.weight
        return output
