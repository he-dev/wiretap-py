import contextlib
import inspect
from typing import Any, Iterator

from tools.elapsed import Elapsed
from tools.welford import Welford
from wiretap import TelemetryScope


class LoopScope:
    """
    This class is used to measure the time taken for a loop.
    """

    def __init__(
            self,
            name: str | None = None,
            dump: dict[str, Any] | None = None,
            tags: set[Any] | None = None,
    ):
        self._name = name
        self._dump = dump or {}
        self._tags = tags or set()
        self.smooth_loops = Welford()
        self.except_loops = Welford()

    @contextlib.contextmanager
    def begin_iteration(
            self,
            dump: dict[str, Any] | None = None,
            tags: set[Any] | None = None,
            **kwargs
    ) -> Iterator[TelemetryScope]:
        """
        Initializes a context manager that measures the time taken for a single iteration.

        :return: The scope that measures the time taken for a single iteration
        extended with the `index` attribute.
        """

        # This is fake as not used anywhere, but the constructor requires it.
        stack = inspect.stack(2)
        frame = stack[2]

        index = (self.smooth_loops.n + self.except_loops.n)
        dump = dump or {}
        dump |= kwargs
        dump |= {"index": index}

        tags = self._tags | (tags or set()) | self._tags
        custom_id = kwargs.pop("id", None)  # The caller can override the default id.
        with TelemetryScope.push(custom_id, self._name, dump, tags, frame) as scope:
            scope.index = index
            elapsed = Elapsed()
            try:
                yield scope
                self.smooth_loops.update(float(elapsed))
            except Exception:
                self.except_loops.update(float(elapsed))
                raise

    def dump(self, precision: int = 3) -> dict[str, Any] | None:
        return {
            "smooth": self.smooth_loops.dump(precision),
            "except": self.except_loops.dump(precision) if self.except_loops.n > 0 else None,
        }
