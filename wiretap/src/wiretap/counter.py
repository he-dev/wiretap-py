import sys
import contextlib
from typing import Any

from _reusable import Elapsed


class LoopCounter:

    def __init__(self, precision: int = 3):
        self.precision = precision
        self.items: int = 0
        self.elapsed: float = 0
        self.min: Reading = Reading(elapsed=sys.float_info.max)
        self.max: Reading = Reading(elapsed=sys.float_info.min)

    @property
    def avg(self) -> float:
        return self.elapsed / self.items if self.items else 0

    @property
    def items_per_second(self) -> float:
        return self.items / self.elapsed if self.items else 0

    @contextlib.contextmanager
    def measure(self, item_id: str | None = None):
        elapsed = Elapsed(self.precision)
        yield
        current = float(elapsed)
        self.items += 1
        self.elapsed += current
        if current < self.min.elapsed:
            self.min = Reading(item_id, current)
        if current > self.max.elapsed:
            self.max = Reading(item_id, current)

    def dump(self) -> dict[str, Any]:
        return {
            "items": self.items,
            "elapsed": self.elapsed,
            "avg": self.avg,
            "min": self.min.dump(),
            "max": self.max.dump(),
            "items_per_second": round(self.items_per_second, self.precision),
            "items_per_minute": round(self.items_per_second * 60, self.precision),
        }


class Reading:
    def __init__(self, item_id: str | None = None, elapsed: float = 0):
        self.item_id = item_id
        self.elapsed = elapsed

    def dump(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "elapsed": self.elapsed,
        }
