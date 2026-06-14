from __future__ import annotations

import logging
import secrets
from contextlib import contextmanager
from contextvars import ContextVar  # noqa: built-in module
from itertools import islice
from typing import Any, ClassVar, Iterator

from wiretap.core.activity import Buzz, Snap
from wiretap.core.activity_status import Fail, Noop, Ready, Void
from wiretap.meta.caller import Caller
from wiretap.util.activity_status import Activity, ActivityStatus
from wiretap.util.activity_bulk import BulkMath
from wiretap.util.activity_feed import PushItem, PushItemOptions, get_state_items, get_state_items_cascading
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
        self._logger: logging.Logger = logging.getLogger(activity.name)

    def __iter__(self) -> Iterator[ActivityScope[Any]]:
        current: ActivityScope[Any] | None = self
        while current:
            yield current
            current = current.parent

    @property
    def depth(self) -> int:
        return self.parent.depth + 1 if self.parent else 0

    def to_dict(self, status: dict[str, Any] | None, state: dict[str, Any] | None) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.scope_id,
            "parent_id": self.parent.scope_id if self.parent else None,
            "activity": {
                "name": self._activity.name,
                "path": PathOf(reversed(list(self)), lambda a: a._activity.name),
                "depth": self.depth,
                "status": status,
                "tags": self._activity.tags
            },
            "state": state,
            "source": self.caller.to_dict() if self.caller else None,
        }

    def message_parts(self, push: PushItem) -> None:
        push("{activity[name]}", "[{activity[status][code]}]", PushItemOptions(separator=None))

    def _log(self, status: ActivityStatus[A]) -> ActivityScope[A]:
        state: dict[str, Any] = {}

        def set_state_item(key: str, value: Any, options: PushItemOptions | None = None) -> None:
            if value is not None:
                state[key] = value

        # core: Get cascading state items from the parent scopes.
        # note: Collect state items from top to bottom so that the last status wins.
        scopes: Iterator[ActivityScope[Any]] = reversed(list(islice(iter(self), 1, None)))
        for scope in scopes:
            get_state_items_cascading(scope._activity, set_state_item)

        # core: Scope, activity, and status each get a chance to fulfill the monitoring contract.
        feeds: list[Any] = [self, self._activity, status]

        for feed in feeds:
            get_state_items(feed, set_state_item)

        extra: dict[str, Any] = self.to_dict(status.to_dict(), state)

        message = self.compose_message(extra, *feeds)
        self._logger.log(status.level, message, extra={"wiretap": extra})
        return self

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
    def __init__(self, activity: A, trace_id: Any | None, caller: Caller | None = None) -> None:
        super().__init__(activity, trace_id, caller)
        self.stopwatch: Stopwatch = Stopwatch()
        self._last_status: tuple[ActivityStatus[A], int] | None = None
        self._duration_ms: int | None = None
        self._bulk_math = BulkMath()

    def to_dict(self, status: dict[str, Any] | None, state: dict[str, Any] | None) -> dict[str, Any]:
        extra = super().to_dict(status, state)
        extra["activity"]["duration_ms"] = self._duration_ms if self._duration_ms is not None else self.stopwatch.elapsed_ms
        return extra

    def _log(self, status: ActivityStatus[A], duration_ms: int | None = None) -> BuzzScope[A]:
        self._duration_ms = duration_ms
        try:
            super()._log(status)
            return self
        finally:
            self._duration_ms = None

    def state_items(self, push: PushItem) -> None:
        self._bulk_math.state_items(push)

    def message_parts(self, push: PushItem) -> None:
        super().message_parts(push)
        push("Duration", "{activity[duration_ms]} ms")
        self._bulk_math.message_parts(push)

    def set_status(self, status: ActivityStatus[A]) -> ActivityScope[A]:
        if self._last_status is not None:
            extra = self.to_dict(status.to_dict(), None)
            _logger.warning(
                "%s status changed from [%s] to [%s] before scope exit.",
                self._activity.name,
                self._last_status[0].code.lower(),
                status.code.lower(),
                extra={"wiretap": extra},
            )
        self._last_status = (status, self.stopwatch.elapsed_ms)
        return self

    def begin_item[B: Buzz](self, activity: B, frame_offset: int = 0) -> ItemScope[B]:
        # core: Begins one item inside this buzz summary.
        if not isinstance(activity, Buzz):
            raise TypeError(f"{type(activity).__qualname__} cannot begin as a bulk item because it is not a Buzz activity.")
        return ItemScope(activity, self._bulk_math, Caller.from_current_frame(frame_offset + 1))

    def __enter__(self) -> BuzzScope[A]:
        self._scope = self.push()
        self._scope.__enter__()
        self._log(Ready())
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if self._last_status is None:
                if exc_type is not None:
                    self._log(Fail(exception=exc))
                else:
                    self._log(Void(reason="Last status not specified and automatically logged."))
            else:
                status, duration_ms = self._last_status
                self._log(status, duration_ms)
        finally:
            self._scope.__exit__(exc_type, exc, tb)


class SnapScope[A: Snap](ActivityScope[A]):
    def log_status(self, status: ActivityStatus[A]) -> SnapScope[A]:
        self._log(status)
        return self

    def message_parts(self, push: PushItem) -> None:
        super().message_parts(push)
        push("Duration", "N/A")

    def __enter__(self) -> SnapScope[A]:
        self._scope = self.push()
        self._scope.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._scope.__exit__(exc_type, exc, tb)


class ItemScope[A: Buzz](BuzzScope[A]):
    def __init__(self, activity: A, bulk_math: BulkMath, caller: Caller | None = None) -> None:
        super().__init__(activity, None, caller)
        self._parent_bulk_math = bulk_math
        self._status: ActivityStatus[A] | None = None

    def set_status(self, status: ActivityStatus[A]) -> ItemScope[A]:
        self._status = status
        super().set_status(status)
        return self

    def __enter__(self) -> ItemScope[A]:
        super().__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            super().__exit__(exc_type, exc, tb)
        finally:
            # core: Each buzz item contributes the final status observed by its own buzz lifecycle.
            self._parent_bulk_math.count(self._status or Noop(), self.stopwatch.elapsed_ms)


def begin_buzz[A: Buzz](activity: A, trace_id: Any | None = None, frame_offset: int = 0, with_caller_info: bool = True) -> BuzzScope[A]:
    if not isinstance(activity, Buzz):
        raise TypeError(f"{type(activity).__qualname__} cannot begin because it is not a Buzz activity.")
    caller = Caller.from_current_frame(frame_offset) if with_caller_info else None
    return BuzzScope(activity, trace_id, caller)


def log_snap[A: Snap](activity: A, status: ActivityStatus[A], trace_id: Any | None = None) -> None:
    with SnapScope(activity, trace_id, Caller.from_current_frame(2)) as scope:
        scope.log_status(status)
