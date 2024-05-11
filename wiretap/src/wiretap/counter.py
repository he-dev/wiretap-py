import contextlib
from typing import Any

from _reusable import Elapsed


class Counter:

    def __init__(self, precision: int = 3):
        self.precision = precision
        self.items: list[Item] = []

    @property
    def count(self) -> int:
        return len(self.items)

    def elapsed(self) -> float:
        return sum(item.elapsed for item in self.items)

    def avg(self) -> float:
        return self.elapsed() / self.count if self.items else 0

    def min(self) -> "Item":
        return min(self.items, key=lambda item: item.elapsed) if self.items else Item()

    def max(self) -> "Item":
        return max(self.items, key=lambda item: item.elapsed) if self.items else Item()

    def items_per_second(self) -> float:
        return self.count / self.elapsed() if self.items else 0

    @contextlib.contextmanager
    def measure(self, item_id: str | None = None):
        elapsed = Elapsed(self.precision)
        yield
        self.items.append(Item(item_id, float(elapsed)))

    def dump(self) -> dict[str, Any]:
        return {
            "items": self.count,
            "elapsed": self.elapsed(),
            "avg": self.avg(),
            "min": self.min().dump(),
            "max": self.max().dump(),
            "items_per_second": round(self.items_per_second(), self.precision),
            "items_per_minute": round(self.items_per_second() * 60, self.precision),
        }


class Item:
    def __init__(self, item_id: str | None = None, elapsed: float = 0):
        self.item_id = item_id
        self.elapsed = elapsed

    def dump(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "elapsed": self.elapsed,
        }
