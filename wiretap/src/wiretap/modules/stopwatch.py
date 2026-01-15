import time
from contextlib import ContextDecorator
from datetime import datetime, timezone


class Stopwatch(ContextDecorator):

    def __init__(self):
        self.start_at = time.time()
        self.start_pc = time.perf_counter_ns()
        self.end_at = self.start_at
        self.end_pc = self.start_pc

    def stop(self) -> float:
        if self.end_pc == self.start_pc:
            self.end_at = time.time()
            self.end_pc = time.perf_counter_ns()
        return self.duration_ms

    @property
    def is_running(self) -> bool:
        return self.end_pc == self.start_pc

    @property
    def duration_ms(self) -> int:
        """Gets the duration in milliseconds."""
        return (self.end_pc - self.start_pc) // 1_000_000

    @property
    def elapsed_ms(self) -> int:
        """Gets the elapsed time in milliseconds."""
        return (time.perf_counter_ns() - self.start_pc) // 1_000_000

    @property
    def start_dt(self) -> datetime:
        return datetime.fromtimestamp(self.start_at, timezone.utc)

    @property
    def end_dt(self) -> datetime:
        return datetime.fromtimestamp(self.end_at, timezone.utc)

    def to_dict(self, iso: bool = False) -> dict:
        # core: Create keys based on the state of the stopwatch.
        return {
            "start_at": self.start_dt.isoformat() if iso else self.start_dt,
            "elapsed_ms": self.elapsed_ms,
        } if self.is_running else {
            "start_at": self.start_dt.isoformat() if iso else self.start_dt,
            "end_at": self.end_dt.isoformat() if iso else self.end_dt,
            "duration_ms": self.duration_ms,
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        self.stop()
