from typing import Any

from wiretap.modules.loop_stats import LoopStats


class LoopRates:
    def __init__(self, stats: dict[str, LoopStats], precision: int = 1):
        self.stats = stats
        self.precision = precision

    @property
    def total_count(self) -> int:
        return sum(stat.count for stat in self.stats.values())

    @property
    def total_elapsed(self) -> float:
        return round(sum(stat.duration_ms for stat in self.stats.values()), self.precision)

    def rate_for(self, category: str) -> float:
        return round(self.stats[category].count / self.total_count, self.precision) if self.total_count else float("nan")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "total_count": self.total_count,
            "total_duration": self.total_elapsed,
        }
        result.update({f"{cat}_rate": self.rate_for(cat) for cat in self.stats})
        return result
