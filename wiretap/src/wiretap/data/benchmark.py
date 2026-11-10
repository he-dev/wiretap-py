from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from time import perf_counter_ns
from typing import Iterator


class Welford:
    """
    Uses the Welford's algorithm because it is an efficient method for computing the mean and standard deviation
    of a dataset in a single pass. It is particularly useful for large datasets or streaming data
    because it avoids the need to store all data points in memory.
    """

    def __init__(self) -> None:
        self.duration_ms: float = 0.0
        self.count: int = 0
        self.mean_ms: float = 0.0
        self.M2: float = 0.0  # Sum of squares of differences from the mean.

    def count_item(self, duration_ms: float) -> None:
        """Counts a single item's duration."""

        self.duration_ms += duration_ms
        self.count += 1
        delta: float = duration_ms - self.mean_ms
        self.mean_ms += delta / self.count
        delta2: float = duration_ms - self.mean_ms
        self.M2 += delta * delta2

    @property
    def variance(self) -> float | None:
        """Calculates the variance of the dataset."""
        if self.count < 2:
            return None  # Not enough data to calculate sample variance.
        return self.M2 / (self.count - 1)  # Sample variance.

    @property
    def std_dev(self) -> float | None:
        """Calculates the standard deviation of the dataset."""
        variance = self.variance
        return variance ** 0.5 if variance is not None else None

    @property
    def throughput_ms(self) -> float:
        """Items per millisecond of measured item time, excluding gaps between items."""
        return self.count / self.duration_ms if self.duration_ms > 0 else 0.0


class Benchmark:
    """Measures items with one overall accumulator and one per classification."""

    def __init__(self) -> None:
        self.total = Welford()
        self._labels: dict[str, Welford] = defaultdict(Welford)

    def __getitem__(self, name: str) -> Welford:
        """Returns the label's accumulator, initially empty for an unseen label."""
        return self._labels[name]

    def ratio(self, label: str, relative_to: str | None = None) -> float | None:
        """Returns a label's count divided by another label's count, or the total if omitted."""
        denominator_count = self.total.count if relative_to is None else self[relative_to].count
        # core: A ratio is undefined when the denominator has no samples.
        if denominator_count == 0:
            return None
        return self[label].count / denominator_count

    @contextmanager
    def measure(self) -> Iterator[Sample]:
        sample = Sample()
        started_ns = perf_counter_ns()
        try:
            yield sample
        finally:
            # core: Measure the whole block once, including samples that raise an exception.
            duration_ms = (perf_counter_ns() - started_ns) / 1_000_000
            self.total.count_item(duration_ms)
            if sample.label is not None:
                self[sample.label].count_item(duration_ms)


class Sample:
    def __init__(self) -> None:
        self.label: str | None = None

    def count_as(self, name: str) -> None:
        # core: A second classification is a programming error, even for the same label.
        if self.label is not None:
            raise ValueError(f"This sample has already been classified as '{self.label!r}'.")
        self.label = name
