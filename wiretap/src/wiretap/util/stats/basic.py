import math
from typing import Any

from wiretap.util.stats import LoopStats, Serializable


class BasicStats(LoopStats, Serializable):
    """
    Uses the Welford's algorithm because it is an efficient method for computing the mean and standard deviation
    of a dataset in a single pass. It is particularly useful for large datasets or streaming data
    because it avoids the need to store all data points in memory.
    """

    def __init__(self, precision: int = 1) -> None:
        self.precision = precision
        self.duration_ms: float = 0.0
        self.count: int = 0
        self.mean: float = 0.0
        self.M2: float = 0.0  # Sum of squares of differences from the mean.

    def count_item(self, duration_ms: float) -> None:
        self.duration_ms += duration_ms
        self.count += 1
        delta: float = self.duration_ms - self.mean
        self.mean += delta / self.count
        delta2: float = self.duration_ms - self.mean
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
    def throughput_ms(self) -> float:
        return self.count / self.duration_ms if self.duration_ms > 0 else float("nan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "elapsed_ms": self.duration_ms,
            "mean": self.mean,
            "std_dev": self.std_dev,
            "throughput_ms": self.throughput_ms,
        } if self.count > 0 else {"count": 0}

    def __str__(self) -> str:
        return str(self.to_dict())