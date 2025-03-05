import math
from typing import Any


class Welford:
    """
    Welford's algorithm is an efficient method for computing the mean and standard deviation
    of a dataset in a single pass. It is particularly useful for large datasets or streaming data
    because it avoids the need to store all data points in memory.
    """

    def __init__(self) -> None:
        self.sum: float = 0.0  # Helper variable for debugging etc.
        self.n: int = 0  # Number of data points.
        self.mean: float = 0.0  # Mean of the data points.
        self.M2: float = 0.0  # Sum of squares of differences from the mean.

    def update(self, x: float) -> None:
        self.sum += x
        self.n += 1
        delta: float = x - self.mean
        self.mean += delta / self.n
        delta2: float = x - self.mean
        self.M2 += delta * delta2

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

    # These properties are not Welford related but make logging easier.

    @property
    def throughput(self) -> float:
        return self.n / self.sum if self.sum > 0 else 0

    def dump(self, precision: int = 3) -> dict[str, Any]:
        if self.n > 0:
            return {
                "count": self.n,
                "elapsed": round(self.sum, precision),
                "mean": round(self.mean, precision),
                "var": round(self.var, precision) if not math.isnan(self.var) else None,
                "std_dev": round(self.std_dev, precision) if not math.isnan(self.std_dev) else None,
                "throughput": {
                    "per_second": round(self.n / self.sum, precision),
                    "per_minute": round(self.n / self.sum * 60, precision),
                }
            }
        else:
            return {
                "count": 0,
            }
