from dataclasses import dataclass
import hashlib


@dataclass(frozen=True)
class VirtualMatrix:
    rows: int = 1_000_000_000
    columns: int = 2_000_000_000
    namespace: str = "neural-matrix-v1"

    def __post_init__(self):
        if self.rows <= 0 or self.columns <= 0:
            raise ValueError("Virtual matrix dimensions must be positive.")

    @property
    def logical_connections(self) -> int:
        return self.rows * self.columns

    def validate_address(self, row: int, column: int) -> None:
        if not 0 <= row < self.rows or not 0 <= column < self.columns:
            raise IndexError("Virtual matrix address out of range.")

    def address_id(self, row: int, column: int) -> int:
        self.validate_address(row, column)
        return row * self.columns + column

    def deterministic_weight(self, row: int, column: int) -> float:
        self.validate_address(row, column)
        key = f"{self.namespace}:{row}:{column}".encode()
        digest = hashlib.blake2b(key, digest_size=8).digest()
        integer = int.from_bytes(digest, "big")
        return (integer / ((1 << 64) - 1)) * 0.2 - 0.1

    def sample_addresses(self, count: int, seed: int = 17) -> list[tuple[int, int]]:
        import random
        if count < 0:
            raise ValueError("count cannot be negative.")
        rng = random.Random(seed)
        return [(rng.randrange(self.rows), rng.randrange(self.columns)) for _ in range(count)]
