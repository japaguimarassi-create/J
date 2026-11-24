from dataclasses import asdict, dataclass

from .config import MatrixConfig


def estimate_runtime_bytes(active_units: int, active_edges: int, expert_count: int, expert_width: int, cache_bytes: int = 0) -> int:
    if min(active_units, expert_count, expert_width) <= 0 or active_edges < 0 or cache_bytes < 0:
        raise ValueError("Invalid capacity dimensions")
    unit_bytes = active_units * 64
    edge_bytes = active_edges * 256
    expert_bytes = expert_count * (expert_width * expert_width * 32 + expert_width * 32)
    return unit_bytes + edge_bytes + expert_bytes + cache_bytes


@dataclass(frozen=True)
class CapacityStage:
    index: int
    active_units: int
    active_edges: int
    estimated_bytes: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


class CapacityPlan:
    def __init__(self, stages: list[CapacityStage], memory_limit_bytes: int):
        if not stages:
            raise ValueError("Capacity plan must contain at least one stage")
        self.stages = tuple(stages)
        self.memory_limit_bytes = memory_limit_bytes

    @classmethod
    def from_config(cls, config: MatrixConfig) -> "CapacityPlan":
        config.validate()
        units = config.active_units
        edges = config.active_edges
        max_units = config.max_active_units
        max_edges = config.max_active_edges
        limit = config.memory_limit_mb * 1024 * 1024
        stages: list[CapacityStage] = []
        while True:
            estimate = estimate_runtime_bytes(
                units, edges, config.expert_count, config.expert_width, config.virtual_cache_mb * 1024 * 1024
            )
            if estimate > limit:
                raise MemoryError(
                    f"Stage with {units} units and {edges} edges exceeds the {config.memory_limit_mb} MiB budget"
                )
            stages.append(CapacityStage(len(stages), units, edges, estimate))
            if units == max_units and edges == max_edges:
                break
            next_units = min(max_units, max(units + 1, units * 2))
            next_edges = min(max_edges, max(edges + 1, edges * 2))
            units, edges = next_units, next_edges
        return cls(stages, limit)

    def to_dict(self) -> dict:
        return {
            "memory_limit_bytes": self.memory_limit_bytes,
            "stages": [stage.to_dict() for stage in self.stages],
        }


class ProgressiveScaler:
    def __init__(self, plan: CapacityPlan):
        self.plan = plan
        self.index = 0

    @property
    def current(self) -> CapacityStage:
        return self.plan.stages[self.index]

    @property
    def has_next(self) -> bool:
        return self.index + 1 < len(self.plan.stages)

    def advance(self) -> CapacityStage:
        if not self.has_next:
            raise StopIteration("Maximum configured capacity reached")
        self.index += 1
        return self.current
