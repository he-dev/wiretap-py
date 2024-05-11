from timeit import default_timer as timer


class Elapsed:

    def __init__(self, precision: int = 3):
        self.precision = precision
        self.start = timer()

    @property
    def current(self) -> float:
        """Gets the current elapsed time in seconds."""
        return round(timer() - self.start, self.precision)

    def __float__(self):
        return self.current
