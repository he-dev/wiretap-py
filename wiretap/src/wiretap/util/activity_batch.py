from typing import Any

from wiretap.util.activity import ActivityStatus
from wiretap.util.activity_feed import PushItem


class BuzzBatch:
    """Internal accumulator used when a buzz processes repeated items."""

    def __init__(self) -> None:
        self.item_count = 0
        self._status_counts: dict[str, int] = {}
        self.duration_ms = 0
        self.duration_ms_min: int | None = None
        self.duration_ms_max: int | None = None
        self._duration_ms_mean = 0.0
        self._duration_ms_m2 = 0.0

    def count(self, status: ActivityStatus[Any], duration_ms: int) -> None:
        # core: Each buzz item contributes exactly one outcome to the parent buzz summary.
        self.item_count += 1
        code = status.code.lower()
        self._status_counts[code] = self._status_counts.get(code, 0) + 1
        self.duration_ms += duration_ms
        self.duration_ms_min = duration_ms if self.duration_ms_min is None else min(self.duration_ms_min, duration_ms)
        self.duration_ms_max = duration_ms if self.duration_ms_max is None else max(self.duration_ms_max, duration_ms)

        # util: Welford's algorithm tracks variance without storing each item duration.
        delta = duration_ms - self._duration_ms_mean
        self._duration_ms_mean += delta / self.item_count
        delta2 = duration_ms - self._duration_ms_mean
        self._duration_ms_m2 += delta * delta2

    def __bool__(self) -> bool:
        # core: A batch only contributes telemetry after at least one buzz item was completed.
        return self.item_count > 0

    @property
    def duration_ms_mean(self) -> float:
        return self._duration_ms_mean

    @property
    def duration_ms_std_dev(self) -> float:
        return (self._duration_ms_m2 / (self.item_count - 1)) ** 0.5 if self.item_count > 1 else 0.0

    @property
    def throughput_s(self) -> float:
        return self.item_count / (self.duration_ms / 1000) if self.duration_ms else 0.0

    def rate_of(self, code: str) -> float:
        return self._status_counts[code] / self.item_count if self.item_count else 0.0

    def state_items(self, push: PushItem) -> None:
        if not self:
            return
        push("item_count", self.item_count)
        for code, count in self._status_counts.items():
            push(f"{code}_count", count)
            push(f"{code}_rate", self.rate_of(code))
        push("duration_ms", self.duration_ms)
        push("duration_ms_mean", self.duration_ms_mean)
        push("duration_ms_min", self.duration_ms_min)
        push("duration_ms_max", self.duration_ms_max)
        push("duration_ms_std_dev", self.duration_ms_std_dev)
        push("throughput_s", self.throughput_s)

    def message_parts(self, push: PushItem) -> None:
        if not self:
            return
        for code in self._status_counts:
            push(code.capitalize(), f"{{state[{code}_rate]:0.1%}} ({{state[{code}_count]}} of {{state[item_count]}})")
        push("Throughput", "{state[throughput_s]:0.1f}/s")
