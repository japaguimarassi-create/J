from dataclasses import dataclass
import hashlib
import random


@dataclass(frozen=True)
class VirtualMatrix:
    rows: int = 1_000_000_000
    columns: int = 2_000_000_000
    namespace: str = "neural-matrix-v1"

    def __post_init__(self):
        for name, value in (("rows", self.rows), ("columns", self.columns)):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"Virtual matrix {name} must be a positive integer")
        if not isinstance(self.namespace, str) or not self.namespace:
            raise ValueError("Virtual matrix namespace must be a non-empty string")

    @property
    def logical_connections(self) -> int:
        return self.rows * self.columns

    def validate_address(self, row: int, column: int) -> None:
        for name, value in (("row", row), ("column", column)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"Virtual matrix {name} address must be an integer")
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
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("count must be a non-negative integer")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")
        rng = random.Random(seed)
        return [(rng.randrange(self.rows), rng.randrange(self.columns)) for _ in range(count)]
