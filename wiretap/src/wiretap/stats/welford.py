import math
from typing import Any

from wiretap.data import LoopStats


class WelfordStats(LoopStats):
    """
    Welford's algorithm is an efficient method for computing the mean and standard deviation
    of a dataset in a single pass. It is particularly useful for large datasets or streaming data
    because it avoids the need to store all data points in memory.
    """

    def __init__(self, precision: int = 3) -> None:
        self.precision = precision
        self.sum: float = 0.0  # Helper variable for debugging etc.
        self.n: int = 0  # Number of data points.
        self.e: int = 0  # Number of errors.
        self.mean: float = 0.0  # Mean of the data points.
        self.M2: float = 0.0  # Sum of squares of differences from the mean.

    @property
    def count(self) -> int:
        return self.n

    def collect(self, elapsed: float, smooth: bool) -> None:
        self.sum += elapsed
        self.n += 1
        delta: float = elapsed - self.mean
        self.mean += delta / self.n
        delta2: float = elapsed - self.mean
        self.M2 += delta * delta2
        if not smooth:
            self.e += 1

    @property
    def var(self) -> float:
        """Calculates the variance of the dataset."""
        if self.n < 2:
            return float('nan')  # Not enough data to calculate variance.
        return self.M2 / (self.n - 1)  # Sample variance.

    @property
    def std_dev(self) -> float:
        """Calculates the standard deviation of the dataset."""
        return self.var ** 0.5  # Standard deviation.

    # These properties are not Welford-related but make logging easier.

    @property
    def throughput(self) -> float:
        return self.n / self.sum if self.sum > 0 else 0

    def dump(self) -> dict[str, Any]:
        if self.n > 0:
            return {
                "count": {
                    "total": self.n,
                    "error": self.e
                },
                "smooth": round((self.n - self.e) / self.n, self.precision) if self.n > 0 else None,
                "elapsed": round(self.sum, self.precision),
                "mean": round(self.mean, self.precision),
                "var": round(self.var, self.precision) if not math.isnan(self.var) else None,
                "std_dev": round(self.std_dev, self.precision) if not math.isnan(self.std_dev) else None,
                "throughput": {
                    "per_second": round(self.n / self.sum, self.precision),
                    "per_minute": round(self.n / self.sum * 60, self.precision),
                }
            }
        else:
            return {
                "count": 0,
            }
