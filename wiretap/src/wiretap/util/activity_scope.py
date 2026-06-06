from __future__ import annotations

import logging
import secrets
from contextlib import contextmanager
from contextvars import ContextVar  # noqa: built-in module
from itertools import islice
from typing import Any, Callable, ClassVar, Iterator

from wiretap.core.activity import Buzz, Snap
from wiretap.core.activity_status import Fail, Noop, Void, Zero
from wiretap.meta.caller import Caller
from wiretap.util.activity import Activity, ActivityStatus, LastStatusCount
from wiretap.util.activity_batch import BuzzBatch
from wiretap.util.activity_feed import get_state_items, get_state_items_cascading
from wiretap.util.activity_message import ComposeMessage, ComposeMessageByAppending
from wiretap.util.path_of import PathOf
from wiretap.util.stopwatch import Stopwatch

# util: Internal logger.
_logger = logging.getLogger("wiretap")


class ActivityScope[A: Activity]:
    _stack: ClassVar[ContextVar[ActivityScope[Any] | None]] = ContextVar("current_activity", default=None)
    compose_message: ClassVar[ComposeMessage] = ComposeMessageByAppending()

    def __init__(self, activity: A, trace_id: Any | None, caller: Caller | None = None) -> None:
        self._activity = activity
        self.trace_id: str = trace_id or secrets.token_hex(16)
        self.scope_id: str = secrets.token_hex(8)  # note: python reserves id already.
        self.parent: ActivityScope[Any] | None = None  # core: This is going to be set on __enter__.
        self.caller = caller
        self.stopwatch: Stopwatch = Stopwatch()
        self._last_status = LastStatusCount()
        self._buzz_batch = BuzzBatch()
        self._logger: logging.Logger = logging.getLogger(activity.name)

    def __iter__(self) -> Iterator[ActivityScope[Any]]:
        current: ActivityScope[Any] | None = self
        while current:
            yield current
            current = current.parent

    @property
    def depth(self) -> int:
        return self.parent.depth + 1 if self.parent else 0

    def to_extra(self, status: str | None, state: dict[str, Any] | None) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.scope_id,
            "parent_id": self.parent.scope_id if self.parent else None,
            "activity": {
                "name": self._activity.name,
                "path": PathOf(reversed(list(self)), lambda a: a._activity.name),
                "depth": self.depth,
                "status": status.lower() if status else None,
                "duration_ms": self.stopwatch.elapsed_ms,
                "tags": self._activity.tags
            },
            "state": state,
            "source": self.caller.to_dict() if self.caller else None,
        }

    def log_status(self, status: ActivityStatus[A]) -> ActivityScope[A]:
        self._last_status.increment()
        return self._log(status)

    def _log(self, status: ActivityStatus[A]) -> ActivityScope[A]:

        state: dict[str, Any] = {}

        def set_state_item(key: str | None, value: Any) -> None:
            if key is not None and value is not None:
                state[key] = value

        # core: Get cascading state items from the parent scopes.
        # note: Collect state items from top to bottom so that the last status wins.
        scopes: Iterator[ActivityScope[Any]] = reversed(list(islice(iter(self), 1, None)))
        for scope in scopes:
            get_state_items_cascading(scope._activity, set_state_item)

        # core: Activity, buzz batch, and status each get a chance to fulfill the monitoring contract.
        state_feeds: list[Any] = [self._activity, self._buzz_batch, status]

        for state_feed in state_feeds:
            get_state_items(state_feed, set_state_item)

        extra: dict[str, Any] = self.to_extra(status.code, state)

        message = self.compose_message(extra, *state_feeds)
        status_level = self.get_status_level_or_default(status)

        # core: Special overflow handling for the last status.
        if self._last_status.overflows:
            status_level = logging.DEBUG
            _logger.warning(f"Last status logged {self._last_status.value} times. This is a bug.")

        self._logger.log(status_level, message, extra={"wiretap": extra})
        return self

    def get_status_level_or_default(self, status: ActivityStatus[A]) -> int:
        # util: Concrete scopes can adjust lifecycle statuses without a global resolver.
        return status.level

    @classmethod
    def current(cls) -> ActivityScope[Any] | None:
        return cls._stack.get()

    @contextmanager
    def push(self) -> Iterator[None]:
        # meta: ContextVar stack mechanics are shared by all concrete scope lifecycles.
        if parent := ActivityScope._stack.get():
            self.parent = parent
            # core: Parent's trace ID needs to be propagated to child scopes.
            self.trace_id = parent.trace_id

        token = ActivityScope._stack.set(self)
        try:
            yield
        finally:
            ActivityScope._stack.reset(token)
            self.parent = None


class BuzzScope[A: Buzz](ActivityScope[A]):
    def get_status_level_or_default(self, status: ActivityStatus[A]) -> int:
        # core: Buzz lifecycle flags can promote automatic lifecycle statuses to core logs.
        match status:
            case Zero():
                if self._activity.must_log_zero:
                    return logging.INFO
            case Void():
                if self._activity.can_log_void:
                    return logging.INFO

        return super().get_status_level_or_default(status)

    def begin_item[B: Activity](self, activity: B, frame_offset: int = 0) -> BuzzItemScope[B]:
        # core: Begins one item inside this buzz summary.
        return BuzzItemScope(activity, self._buzz_batch, self.trace_id, Caller.from_current_frame(frame_offset + 1))

    def __enter__(self) -> BuzzScope[A]:
        self._scope = self.push()
        self._scope.__enter__()
        self._log(Zero())
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if self._last_status.is_zero:
                if exc_type is not None:
                    self._log(Fail(exception=exc))
                else:
                    self._log(Void(reason="Last status not specified and automatically logged."))
        finally:
            self._scope.__exit__(exc_type, exc, tb)


class SnapScope[A: Snap](ActivityScope[A]):
    def __enter__(self) -> SnapScope[A]:
        self._scope = self.push()
        self._scope.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._scope.__exit__(exc_type, exc, tb)


class BuzzItemStatus[A: Activity]:
    def __init__(self, log: Callable[[], None]) -> None:
        self._log = log

    def log(self) -> None:
        self._log()


class BuzzItemScope[A: Activity](ActivityScope[A]):
    def __init__(self, activity: A, batch: BuzzBatch, trace_id: Any | None, caller: Caller | None = None) -> None:
        super().__init__(activity, trace_id, caller)
        self._batch = batch
        self._status: ActivityStatus[A] | None = None

    def set_status(self, status: ActivityStatus[A]) -> BuzzItemStatus[A]:
        self._status = status

        # util: Adapts log_status, which returns the scope, into a terminal status action.
        def log() -> None:
            self.log_status(status)

        return BuzzItemStatus(log)

    def log_status(self, status: ActivityStatus[A]) -> BuzzItemScope[A]:
        super().log_status(status)
        return self

    def __enter__(self) -> BuzzItemScope[A]:
        self._scope = self.push()
        self._scope.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            # core: A buzz item without an explicit status is intentionally inconclusive.
            self._batch.count(self._status or Noop(), self.stopwatch.elapsed_ms)
        finally:
            self._scope.__exit__(exc_type, exc, tb)


def begin_buzz[A: Buzz](activity: A, trace_id: Any | None = None, frame_offset: int = 0, with_caller_info: bool = True) -> BuzzScope[A]:
    if not isinstance(activity, Buzz):
        raise TypeError(f"{type(activity).__qualname__} cannot begin because it is not a Buzz activity.")
    caller = Caller.from_current_frame(frame_offset) if with_caller_info else None
    return BuzzScope(activity, trace_id, caller)


def log_status[A: Snap](snap: A, flag: ActivityStatus[A], trace_id: Any | None = None) -> None:
    with SnapScope(snap, trace_id, Caller.from_current_frame(2)) as scope:
        scope.log_status(flag)
