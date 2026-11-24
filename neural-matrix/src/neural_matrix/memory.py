from collections import OrderedDict
from contextlib import contextmanager
from threading import RLock
from typing import Iterator

from .virtual import VirtualMatrix


class MemoryBudgetExceeded(MemoryError):
    pass


class MemoryBudget:
    def __init__(self, max_bytes: int):
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        self.max_bytes = int(max_bytes)
        self._cache: OrderedDict[object, tuple[object, int]] = OrderedDict()
        self._reserved = 0
        self._cached = 0
        self._lock = RLock()

    @property
    def used_bytes(self) -> int:
        with self._lock:
            return self._reserved + self._cached

    @property
    def cached_items(self) -> int:
        with self._lock:
            return len(self._cache)

    def get(self, key: object, default=None):
        with self._lock:
            item = self._cache.get(key)
            if item is None:
                return default
            self._cache.move_to_end(key)
            return item[0]

    def put(self, key: object, value: object, size_bytes: int = 64) -> None:
        size_bytes = int(size_bytes)
        if size_bytes <= 0:
            raise ValueError("size_bytes must be positive")
        if size_bytes > self.max_bytes:
            raise MemoryBudgetExceeded("Item is larger than the entire memory budget")
        with self._lock:
            previous = self._cache.pop(key, None)
            if previous is not None:
                self._cached -= previous[1]
            self._evict_until_fits(size_bytes)
            self._cache[key] = (value, size_bytes)
            self._cached += size_bytes

    def _evict_until_fits(self, incoming: int) -> None:
        if incoming > self.max_bytes - self._reserved:
            raise MemoryBudgetExceeded("Active reservations leave insufficient memory budget")
        while self._reserved + self._cached + incoming > self.max_bytes and self._cache:
            _, (_, size) = self._cache.popitem(last=False)
            self._cached -= size
        if self._reserved + self._cached + incoming > self.max_bytes:
            raise MemoryBudgetExceeded("Active reservations leave insufficient cache budget")

    @contextmanager
    def reserve(self, size_bytes: int) -> Iterator[None]:
        size_bytes = int(size_bytes)
        if size_bytes < 0:
            raise ValueError("size_bytes cannot be negative")
        with self._lock:
            self._evict_until_fits(size_bytes)
            self._reserved += size_bytes
        try:
            yield
        finally:
            with self._lock:
                self._reserved -= size_bytes

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                "limit_bytes": self.max_bytes,
                "reserved_bytes": self._reserved,
                "cached_bytes": self._cached,
                "used_bytes": self._reserved + self._cached,
                "cached_items": len(self._cache),
            }


class VirtualWeightCache:
    def __init__(self, matrix: VirtualMatrix, budget: MemoryBudget, item_bytes: int = 128):
        if item_bytes <= 0:
            raise ValueError("item_bytes must be positive")
        self.matrix = matrix
        self.budget = budget
        self.item_bytes = item_bytes

    def get(self, row: int, column: int) -> float:
        address = self.matrix.address_id(row, column)
        cached = self.budget.get(address)
        if cached is not None:
            return float(cached)
        weight = self.matrix.deterministic_weight(row, column)
        self.budget.put(address, weight, self.item_bytes)
        return weight
