from timeit import default_timer as timer


class Elapsed:

    def __init__(self):
        self.start = timer()

    @property
    def value(self) -> float:
        """Gets the current elapsed time in seconds."""
        return timer() - self.start

    def __float__(self):
        return self.value
