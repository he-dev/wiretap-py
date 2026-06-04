import math
from collections import defaultdict
from typing import Any


class LoopStats:
    """
    Uses the Welford's algorithm because it is an efficient method for computing the mean and standard deviation
    of a dataset in a single pass. It is particularly useful for large datasets or streaming data
    because it avoids the need to store all data points in memory.
    """

    def __init__(self) -> None:
        self.duration_ms: int = 0
        self.count: int = 0
        self.mean: float = 0.0
        self.M2: float = 0.0  # Sum of squares of differences from the mean.
        self.status: dict[str, int] = defaultdict(int)

    def count_item(self, status: SpanStatus, duration_ms: int) -> None:
        """Counts a single item's duration."""

        self.status[status] += 1
        self.duration_ms += duration_ms
        self.count += 1
        delta: float = duration_ms - self.mean
        self.mean += delta / self.count
        delta2: float = duration_ms - self.mean
        self.M2 += delta * delta2

    @property
    def var(self) -> float:
        """Calculates the variance of the dataset."""
        if self.count < 2:
            return float("nan")  # Not enough data to calculate variance.
        return self.M2 / (self.count - 1)  # Sample variance.

    @property
    def std_dev(self) -> float:
        """Calculates the standard deviation of the dataset."""
        return self.var ** 0.5 if not math.isnan(self.var) else float("nan")  # Standard deviation.

    @property
    def throughput_ms(self) -> int:
        return self.count // self.duration_ms if self.duration_ms > 0 else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_count": self.count,
            "success_count": self.status[SpanStatus.OK.value],
            "success_rate": self.status[SpanStatus.OK.value] / self.count,
            "error_count": self.status[SpanStatus.ERROR.value],
            "error_rate": self.status[SpanStatus.ERROR.value] / self.count,
            "duration_ms": self.duration_ms,
            "throughput_ms": self.throughput_ms,
            "mean": self.mean,
            "std_dev": self.std_dev,
        } if self.count > 0 else {"count": 0}

    def __str__(self) -> str:
        return str(self.to_dict())


class CountEvent:
    def __init__(self, stats: LoopStats) -> None:
        self.stats = stats

    def __call__(self, span: Span) -> None:
        self.stats.count_item(span.status, span.stopwatch.elapsed_ms)
