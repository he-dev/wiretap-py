from __future__ import annotations

import logging
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Annotated, Generic

from wiretap.util.activity_scope import (
    Activity,
    ActivityScope,
    AddStateItem,
    AppendMessagePart,
    Buzz,
    Fail,
    MessagePart,
    Okay,
    StateItem,
    Void,
)


@dataclass
class ProcessBatch(Buzz):
    """Draft contract for observing a batch-like activity.

    The activity is the stable monitoring contract. A specialized scope owns the
    runtime counters and contributes them to the final status log.
    """

    # core: Identifies the batch contract independently from the code that processes it.
    batch_name: Annotated[str, StateItem(inheritable=True), MessagePart("Batch")]

    @property
    def name(self) -> str:
        return self.batch_name

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

    def count(self, status: str, duration_ms: int) -> None:
        # core: Each iteration contributes exactly one outcome to the batch summary.
        self.total_count += 1
        self.duration_ms += duration_ms

        match status:
            case "okay":
                self.okay_count += 1
            case "fail":
                self.fail_count += 1
            case _:
                self.void_count += 1

    @property
    def mean_duration_ms(self) -> float:
        return self.duration_ms / self.total_count if self.total_count else 0.0

    @property
    def error_rate(self) -> float:
        return self.fail_count / self.total_count if self.total_count else 0.0

    @property
    def success_rate(self) -> float:
        return self.okay_count / self.total_count if self.total_count else 0.0

    def state_items(self, add: AddStateItem) -> None:
        add("total_count", self.total_count)
        add("okay_count", self.okay_count)
        add("fail_count", self.fail_count)
        add("void_count", self.void_count)
        add("duration_ms", self.duration_ms)
        add("mean_duration_ms", self.mean_duration_ms)
        add("success_rate", self.success_rate)
        add("error_rate", self.error_rate)

    def message_parts(self, append: AppendMessagePart) -> None:
        append("Items: {total_count}")
        append("Okay: {okay_count}")
        append("Failed: {fail_count}")
        append("Void: {void_count}")


class BatchItem(AbstractContextManager["BatchItem"]):
    def __init__(self, stats: BatchStats) -> None:
        # meta: Delays the import so this draft helper stays light during module loading.
        from wiretap.util.stopwatch import Stopwatch

        self._stats = stats
        self._stopwatch = Stopwatch()
        self._status: str | None = None

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


class ProcessBatchScope[A: Activity](ActivityScope[A], Generic[A]):
    """Draft specialized scope for batch contracts.

    Intended usage:

        with wiretap.begin_buzz(ProcessBatch("import-users")) as batch:
            with batch.item() as item:
                import_user(user)
                item.okay()

            batch.log_status(ProcessBatch.Okay())

    The missing core integration is small: ActivityScope._log should collect
    state/message parts from `self` between the activity and status sources.
    Then this scope can contribute BatchStats through the existing protocols.
    """

    def __init__(self, activity: A, trace_id: Any | None, caller: Any | None = None) -> None:
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


def begin_process_batch(activity: ProcessBatch, trace_id: Any | None = None) -> ProcessBatchScope[ProcessBatch]:
    """Draft convenience constructor until begin_buzz can select custom scopes."""

    # todo: Replace this helper once begin_buzz can select a scope type from the activity.
    logging.getLogger(__name__).warning(
        "begin_process_batch is a draft helper. The intended final shape is "
        "begin_buzz(activity) returning the activity's configured scope type."
    )
    return ProcessBatchScope(activity, trace_id)
