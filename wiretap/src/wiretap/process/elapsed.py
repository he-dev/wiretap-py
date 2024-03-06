from timeit import default_timer as timer


class Elapsed:
    _start: float | None = None

    @property
    def current(self) -> float:
        """Gets the current elapsed time in seconds or 0 if called for the first time."""
        if self._start:
            return timer() - self._start
        else:
            self._start = timer()
            return .0

    def __float__(self):
        return self.current
