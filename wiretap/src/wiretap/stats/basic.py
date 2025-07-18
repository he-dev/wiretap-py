from typing import Any

from wiretap.util import LoopStats


class BasicStats(LoopStats):

    def __init__(self, precision: int = 3) -> None:
        self.precision = precision
        self.sum: float = 0.0
        self.n: int = 0  # Number of data points.
        self.e: int = 0  # Number of errors.
        self.mean: float = 0.0  # Mean of the data points.

    @property
    def count(self) -> int:
        return self.n

    def collect(self, elapsed: float, smooth: bool) -> None:
        self.sum += elapsed
        self.n += 1
        delta: float = elapsed - self.mean
        self.mean += delta / self.n
        if not smooth:
            self.e += 1

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
                "throughput": {
                    "per_second": round(self.n / self.sum, self.precision),
                    "per_minute": round(self.n / self.sum * 60, self.precision),
                }
            }
        else:
            return {
                "count": 0,
            }
