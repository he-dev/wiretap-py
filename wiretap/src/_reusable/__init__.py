import itertools
from importlib import import_module
from typing import TypeVar, Optional, Iterable, Type, Any

from .elapsed import Elapsed
from .node import Node

T = TypeVar('T')


def nth_or_default_(source: list[T], index: int) -> Optional[T]:
    return source[index] if index < len(source) else None


def nth_or_default(source: Iterable[T], index: int, default: Optional[T] = None) -> Optional[T]:
    return next(itertools.islice(source, index, None), default)


def resolve_class(name: str) -> Type:
    # Parses the path and loads the class it dynamically.
    *module_names, class_name = name.split(".")
    return getattr(import_module(".".join(module_names)), class_name)


def map_to_str(values: Iterable[Any] | None) -> set[str]:
    return set(map(lambda x: str(x), values)) if values else set()


class Welford:
    """
    Welford's algorithm is an efficient method for computing the mean and standard deviation
    of a dataset in a single pass. It is particularly useful for large datasets or streaming data
    because it avoids the need to store all data points in memory.
    """

    def __init__(self) -> None:
        self.n: int = 0  # Number of data points.
        self.mean: float = 0.0  # Mean of the data points.
        self.M2: float = 0.0  # Sum of squares of differences from the mean.

    def update(self, x: float) -> None:
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
