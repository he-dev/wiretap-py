from __future__ import annotations
import contextlib
import logging
import secrets
import sys
from contextvars import ContextVar  # noqa: built-in module
from enum import Enum, auto, IntEnum
from functools import cached_property
from typing import Optional, Any, Iterator, TypeVar, ClassVar

from wiretap.util.stopwatch import Stopwatch

T = TypeVar("T", bound="ActivityScope")


class ActivityEvent(IntEnum):
    ZERO = auto()
    TICK = auto()
    LAST = auto()


class MoveNextEvent(IntEnum):
    OKAY = auto()
    INVALID_EVENT_SEQUENCE = auto()


DOMAIN = {"@story": "domain"}
"""Marks a log entry as part of the application's domain behavior."""

SYSTEM = {"@story": "system"}
"""Marks a log entry as technical or infrastructure-related."""

ZERO = {"activity.event": ActivityEvent.ZERO.name.lower()}
TICK = {"activity.event": ActivityEvent.TICK.name.lower()}
LAST = {"activity.event": ActivityEvent.LAST.name.lower()}


class ActivityScope:
    """
    This class represents a single activity scope.
    """

    _stack: ClassVar[ContextVar[Optional["ActivityScope"]]] = ContextVar("current_activity", default=None)

    def __init__(
            self,
            about: str,
            state: dict[str, Any],
            trace_id: Any | None,
            parent: Optional["ActivityScope"] = None,
            parent_id: str | None = None,
    ):
        """
        Initializes a new ActivityScope instance.

        Args:
            about: The name of the activity.
            state: The initial state of the activity.
            trace_id: The trace ID for the activity.
            parent: The parent activity.
            parent_id: External parent span ID, used when there is no local parent activity.
        """
        self.about = about
        self.parent = parent
        self.parent_id = parent.span_id if parent else parent_id
        self.depth: int = parent.depth + 1 if parent else 0
        self.trace_id: str = trace_id or (parent.trace_id if parent else secrets.token_hex(16))
        self.span_id: str = secrets.token_hex(8)
        self.state = parent.state | state if parent else state

        # note: Uses "recent" and not "last" because there is a "last" event, so it would be ambiguous.
        self.recent_event: Optional[ActivityEvent] = None
        self.stopwatch: Stopwatch = Stopwatch()
        self.duration_ms: int = 0

    def __iter__(self) -> Iterator["ActivityScope"]:
        current: Optional["ActivityScope"] = self
        while current:
            yield current
            current = current.parent

    @property
    def trace(self) -> dict:
        return {
            "id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
        }

    def move_next(self, next_event: ActivityEvent) -> str | None:
        match next_event:
            case ActivityEvent.ZERO if self.recent_event is None:
                self.stopwatch = Stopwatch()
            case ActivityEvent.TICK if self.recent_event in (ActivityEvent.ZERO, ActivityEvent.TICK):
                pass
            case ActivityEvent.LAST if self.recent_event in (ActivityEvent.ZERO, ActivityEvent.TICK):
                self.duration_ms = self.stopwatch.elapsed_ms
            case _:
                # core: The requested transition from one event to the next is not valid.
                # return MoveNextEvent.INVALID_EVENT_SEQUENCE

                match next_event:
                    case ActivityEvent.ZERO:
                        return "zero-must-occur-only-once"
                    case ActivityEvent.TICK:
                        return "tick-must-follow-zero-or-tick"
                    case ActivityEvent.LAST if self.recent_event is None:
                        return "last-must-follow-zero-or-tick"
                    case ActivityEvent.LAST if self.recent_event is ActivityEvent.LAST:
                        return "last-must-occur-only-once"

        self.recent_event = next_event
        return None

    # Transition 'last -> last' does not follow 'none -> zero(1) -> tick(0-n) -> last(1)'

    @classmethod
    @contextlib.contextmanager
    def push(
            cls,
            about: str,
            state: dict[str, Any],
            trace_id: Any | None = None,
            parent_id: str | None = None,
    ) -> Iterator["ActivityScope"]:
        """
        Creates and pushes a child of the current activity-scope onto the stack.
        """

        activity = cls(
            about=about,
            state=state,
            trace_id=trace_id,
            parent=cls.get_current(),
            parent_id=parent_id,
        )
        token = cls._stack.set(activity)
        try:
            yield activity
        finally:
            cls._stack.reset(token)

    # note: There is no builtin @classproperty! :-\
    @classmethod
    def get_current(cls) -> Optional["ActivityScope"]:
        return cls._stack.get()


class ActivityAbout:
    def __init__(self, activity: ActivityScope) -> None:
        self._activity = activity

    @property
    def elapsed_ms(self) -> int:
        return self._activity.stopwatch.elapsed_ms

    @cached_property
    def zero(self) -> ActivityLogger:
        return ActivityLogger(self._activity, ActivityEvent.ZERO)

    @cached_property
    def tick(self) -> ActivityLogger:
        return ActivityLogger(self._activity, ActivityEvent.TICK)

    @cached_property
    def last(self) -> ActivityLogger:
        return ActivityLogger(self._activity, ActivityEvent.LAST)


class ActivityLogger:
    def __init__(self, activity: ActivityScope, event: ActivityEvent) -> None:
        self._activity = activity
        self._event = event
        self.logger: logging.Logger = logging.getLogger(activity.about)

    def _log(
            self,
            message: str | None,
            level: int,
            **kwargs
    ) -> None:
        move_result = self._activity.move_next(self._event)

        if not self.logger.isEnabledFor(level):
            return

        stack_level = kwargs.pop("stack_level", 3)
        context = self._activity.state.copy()
        context.update(kwargs)

        activity = {
            "about": self._activity.about,
            "event": self._event.name,
            "depth": self._activity.depth,
        }

        if self._event is ActivityEvent.LAST:
            activity["duration_ms"] = self._activity.duration_ms

        extra: dict[str, Any] = {
            "_wiretap": True,
            "context": context,
            "activity": activity,
            "trace": self._activity.trace,
        }

        if move_result is not None:
            extra["fixme"] = [move_result]

        self.logger.log(
            level=level,
            msg=message,
            exc_info=sys.exc_info()[0] is not None,
            extra=extra,
            stacklevel=stack_level
        )

    def log_debug(self, message: str | None, **kwargs) -> None:
        self._log(message, logging.DEBUG, **kwargs)

    def log_info(self, message: str | None, **kwargs) -> None:
        self._log(message, logging.INFO, **kwargs)

    def log_warning(self, message: str | None, **kwargs) -> None:
        self._log(message, logging.WARNING, **kwargs)

    def log_error(self, message: str | None, **kwargs) -> None:
        self._log(message, logging.ERROR, **kwargs)
