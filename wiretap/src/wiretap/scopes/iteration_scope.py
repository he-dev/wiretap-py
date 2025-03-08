import contextlib
from typing import Any, Iterator

from tools.elapsed import Elapsed
from tools.welford import Welford


class IterationIncomplete:
    """
    This class is used to signal that an iteration was incomplete.
    """

    def __init__(self):
        self._value = False

    def __call__(self):
        self._value = True

    def __bool__(self):
        return self._value


class IterationScope:
    """
    This class is used to measure the time taken for each iteration.
    """
    def __init__(self):
        self.smooth_loops = Welford()
        self.except_loops = Welford()

    @contextlib.contextmanager
    def __call__(self, item_id: str | None = None) -> Iterator[IterationIncomplete]:
        """
        Initializes a context manager that measures the time taken for a single iteration.
        """

        elapsed = Elapsed()
        incomplete = IterationIncomplete()

        yield incomplete

        if incomplete:
            self.except_loops.update(float(elapsed))
        else:
            self.smooth_loops.update(float(elapsed))

    def dump(self, precision: int = 3) -> dict[str, Any] | None:
        return {
            "smooth": self.smooth_loops.dump(precision),
            "except": self.except_loops.dump(precision),
        }
