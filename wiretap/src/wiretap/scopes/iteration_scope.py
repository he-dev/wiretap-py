import contextlib
from typing import Any, Iterator

from tools.elapsed import Elapsed
from tools.welford import Welford


class IterationAbort:
    def __init__(self):
        self._value = False

    def __call__(self):
        self._value = True

    def __bool__(self):
        return self._value


class IterationScope:

    def __init__(self):
        self.smooth_loops = Welford()
        self.except_loops = Welford()

    @contextlib.contextmanager
    def __call__(self, item_id: str | None = None) -> Iterator[IterationAbort]:
        elapsed = Elapsed()
        abort = IterationAbort()

        yield abort

        if abort:
            self.except_loops.update(float(elapsed))
        else:
            self.smooth_loops.update(float(elapsed))

    def dump(self, precision: int = 3) -> dict[str, Any] | None:
        return {
            "smooth": self.smooth_loops.dump(precision),
            "except": self.except_loops.dump(precision),
        }
