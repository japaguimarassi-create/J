from dataclasses import dataclass


@dataclass(frozen=True)
class MatrixConfig:
    logical_units: int = 1_000_000_000
    logical_connections: int = 2_000_000_000
    active_units: int = 256
    active_edges: int = 2_048
    expert_count: int = 8
    expert_width: int = 32
    top_k_experts: int = 2
    learning_rate: float = 1e-3
    seed: int = 17
    max_active_units: int = 4_096
    max_active_edges: int = 32_768
    memory_limit_mb: int = 256
    max_workers: int = 4

    def validate(self) -> None:
        if self.logical_units <= 0 or self.logical_connections <= 0:
            raise ValueError("Logical dimensions must be positive.")
        if self.active_units <= 0 or self.active_edges < 0:
            raise ValueError("Active graph limits are invalid.")
        if self.active_units > self.logical_units:
            raise ValueError("Active units cannot exceed logical units.")
        if self.active_edges > self.logical_connections:
            raise ValueError("Active edges cannot exceed logical connections.")
        if self.expert_count <= 0 or self.expert_width <= 0:
            raise ValueError("Expert dimensions must be positive.")
        if not 1 <= self.top_k_experts <= self.expert_count:
            raise ValueError("top_k_experts must be within expert_count.")
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive.")
        if self.max_active_units < self.active_units:
            raise ValueError("max_active_units cannot be below active_units.")
        if self.max_active_edges < self.active_edges:
            raise ValueError("max_active_edges cannot be below active_edges.")
        if self.memory_limit_mb <= 0 or self.max_workers <= 0:
            raise ValueError("Memory and worker limits must be positive.")
