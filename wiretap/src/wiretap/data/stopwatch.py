from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter_ns


@dataclass(frozen=True)
class Timespan:
    start_utc: datetime
    end_utc: datetime
    duration_ms: int


class Stopwatch:
    def __init__(self) -> None:
        self._start_utc = datetime.now(timezone.utc)
        self._start_pc = perf_counter_ns()

    @property
    def elapsed(self) -> Timespan:
        end_pc = perf_counter_ns()
        end_utc = datetime.now(timezone.utc)

        return Timespan(
            start_utc=self._start_utc,
            end_utc=end_utc,
            duration_ms=(end_pc - self._start_pc) // 1_000_000,
        )
