from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Annotated, Literal

from wiretap.util.activity_scope import (
    Activity,
    ActivityScope,
    AddStateItem,
    AppendMessagePart,
    Buzz,
    Caller,
    Fail,
    MessagePart,
    Okay,
    StateItem,
    Void,
)


type BatchItemStatus = Literal["okay", "fail", "void"]


@dataclass
class ProcessBatch(Buzz):
    """Draft contract for observing a batch-like activity.

    The activity is the stable monitoring contract. A specialized scope owns the
    runtime counters and contributes them to the final status log.
    """

    # core: Identifies the batch contract independently from the code that processes it.
    batch_name: Annotated[str, StateItem(cascade=True)]

    @property
    def name(self) -> str:
        return self.batch_name

    def create_scope(self, trace_id: Any | None, caller: Caller | None) -> ProcessBatchScope[ProcessBatch]:
        return ProcessBatchScope(self, trace_id, caller)

    @dataclass
    class Okay(Okay["ProcessBatch"]):
        pass

    @dataclass
    class Fail(Fail["ProcessBatch"]):
        pass

    @dataclass
    class Void(Void["ProcessBatch"]):
        pass


class BatchStats:
    """Internal accumulator used by ProcessBatchScope.

    This deliberately stays implementation-side. It contributes aggregate state
    through the same protocols used by activities and statuses.
    """

    def __init__(self) -> None:
        self.total_count = 0
        self.okay_count = 0
        self.fail_count = 0
        self.void_count = 0
        self.duration_ms = 0
        self.duration_ms_min: int | None = None
        self.duration_ms_max: int | None = None
        self._duration_ms_mean = 0.0
        self._duration_ms_m2 = 0.0

    def count(self, status: BatchItemStatus, duration_ms: int) -> None:
        # core: Each iteration contributes exactly one outcome to the batch summary.
        self.total_count += 1
        self.duration_ms += duration_ms
        self.duration_ms_min = duration_ms if self.duration_ms_min is None else min(self.duration_ms_min, duration_ms)
        self.duration_ms_max = duration_ms if self.duration_ms_max is None else max(self.duration_ms_max, duration_ms)

        # util: Welford's algorithm tracks variance without storing each item duration.
        delta = duration_ms - self._duration_ms_mean
        self._duration_ms_mean += delta / self.total_count
        delta2 = duration_ms - self._duration_ms_mean
        self._duration_ms_m2 += delta * delta2

        match status:
            case "okay":
                self.okay_count += 1
            case "fail":
                self.fail_count += 1
            case _:
                self.void_count += 1

    @property
    def duration_ms_mean(self) -> float:
        return self._duration_ms_mean

    @property
    def duration_ms_std_dev(self) -> float:
        return (self._duration_ms_m2 / (self.total_count - 1)) ** 0.5 if self.total_count > 1 else 0.0

    @property
    def fail_rate(self) -> float:
        return self.fail_count / self.total_count if self.total_count else 0.0

    @property
    def okay_rate(self) -> float:
        return self.okay_count / self.total_count if self.total_count else 0.0

    @property
    def void_rate(self) -> float:
        return self.void_count / self.total_count if self.total_count else 0.0

    @property
    def throughput_s(self) -> float:
        return self.total_count / (self.duration_ms / 1000) if self.duration_ms else 0.0

    def state_items(self, add: AddStateItem) -> None:
        add("total_count", self.total_count)
        add("okay_count", self.okay_count)
        add("fail_count", self.fail_count)
        add("void_count", self.void_count)
        add("duration_ms", self.duration_ms)
        add("duration_ms_mean", self.duration_ms_mean)
        add("duration_ms_min", self.duration_ms_min)
        add("duration_ms_max", self.duration_ms_max)
        add("duration_ms_std_dev", self.duration_ms_std_dev)
        add("okay_rate", self.okay_rate)
        add("fail_rate", self.fail_rate)
        add("void_rate", self.void_rate)
        add("throughput_s", self.throughput_s)

    def message_parts(self, append: AppendMessagePart) -> None:
        append("Items: {state[total_count]}")
        append("Okay: {state[okay_count]} ({state[okay_rate]:0.1%})")
        append("Throughput: {state[throughput_s]:0.1f}/s")


class BatchItem(AbstractContextManager["BatchItem"]):
    def __init__(self, stats: BatchStats) -> None:
        # meta: Delays the import so this draft helper stays light during module loading.
        from wiretap.util.stopwatch import Stopwatch

        self._stats = stats
        self._stopwatch = Stopwatch()
        self._status: BatchItemStatus | None = None

    def okay(self) -> None:
        self._status = "okay"

    def fail(self) -> None:
        self._status = "fail"

    def void(self) -> None:
        self._status = "void"

    def __enter__(self) -> BatchItem:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any) -> None:
        # core: Exceptions classify the item as failed unless user code already did so explicitly.
        if exc_type is not None:
            self.fail()
        self._stats.count(self._status or "void", self._stopwatch.elapsed_ms)


class ProcessBatchScope[A: Activity](ActivityScope[A]):
    """Draft specialized scope for batch contracts.

    Intended usage:

        with wiretap.begin_buzz(ProcessBatch("import-users")) as batch:
            with batch.item() as item:
                import_user(user)
                item.okay()

            batch.log_status(ProcessBatch.Okay())

    ActivityScope._log collects state/message parts from `self` between the
    activity and status sources. That lets this scope contribute BatchStats
    through the existing protocols.
    """

    def __init__(self, activity: A, trace_id: Any | None, caller: Caller | None = None) -> None:
        super().__init__(activity, trace_id, caller)
        self._stats = BatchStats()

    def item(self) -> BatchItem:
        # util: Gives callers a discoverable way to track one iteration.
        return BatchItem(self._stats)

    def state_items(self, add: AddStateItem) -> None:
        if self._stats.total_count == 0:
            return
        self._stats.state_items(add)

    def message_parts(self, append: AppendMessagePart) -> None:
        if self._stats.total_count == 0:
            return
        self._stats.message_parts(append)
