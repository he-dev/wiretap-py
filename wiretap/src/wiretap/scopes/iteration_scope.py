import contextlib
import inspect
from typing import Any, Iterator

from tools.elapsed import Elapsed

from wiretap import TelemetryScope, LoopStats


class IterationScope(TelemetryScope):
    index: int


class LoopScope:
    """
    This class is used to measure the time taken for a loop.
    """

    def __init__(
            self,
            name: str | None,
            dump: dict[str, Any] | None,
            tags: set[Any] | None,
            stats: LoopStats
    ):
        self._name = name
        self._dump = dump or {}
        self._tags = tags or set()
        self._stats = stats

    @contextlib.contextmanager
    def begin_iteration(
            self,
            dump: dict[str, Any] | None = None,
            tags: set[Any] | None = None,
            **kwargs
    ) -> Iterator[IterationScope]:
        """
        Initializes a context manager that measures the time taken for a single iteration.

        :return: The scope that measures the time taken for a single iteration
        extended with the `index` attribute.
        """

        # This is fake as not used anywhere, but the constructor requires it.
        stack = inspect.stack(2)
        frame = stack[2]

        index = self._stats.count
        dump = dump or {}
        dump |= kwargs
        dump |= {"index": index}

        tags = self._tags | (tags or set()) | self._tags
        custom_id = kwargs.pop("id", None)  # The caller can override the default id.
        with IterationScope.push(custom_id, self._name, dump, tags, frame) as scope:
            scope.index = index
            elapsed = Elapsed()
            try:
                yield scope
                self._stats.collect(float(elapsed), smooth=True)
            except Exception:
                self._stats.collect(float(elapsed), smooth=False)
                raise
            finally:
                del scope.index

    def dump(self) -> dict[str, Any] | None:
        return {"stats": self._stats.dump()}
