from __future__ import annotations
import contextlib
import logging
import secrets
import sys
from contextvars import ContextVar  # noqa: built-in module
from dataclasses import dataclass
from enum import Enum, auto, IntEnum
from functools import cached_property
from typing import Optional, Any, Iterator, TypeVar, ClassVar

from wiretap.util.stopwatch import Stopwatch

T = TypeVar("T", bound="ActivityScope")


@dataclass(frozen=True)
class Fixme:
    constraints: list[str]


class ActivityEvent(IntEnum):
    ZERO = auto()
    TICK = auto()
    LAST = auto()


class ActivityEventMode(Enum):
    FALLBACK = auto()
    REGULAR = auto()


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
        self.state: dict = parent.state | state if parent else state

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

    def move_next(self, next_event: ActivityEvent, mode: ActivityEventMode) -> Fixme | None:
        match next_event, self.recent_event, mode:
            # core: This is the very first zero, in either mode.
            case ActivityEvent.ZERO, None, ActivityEventMode.REGULAR | ActivityEventMode.FALLBACK:
                self.stopwatch = Stopwatch()
                self.recent_event = next_event
                return Fixme([])

            # core: This zero follows an existing event instead of starting the activity.
            case ActivityEvent.ZERO, ActivityEvent.ZERO | ActivityEvent.TICK | ActivityEvent.LAST, ActivityEventMode.REGULAR | ActivityEventMode.FALLBACK:
                self.recent_event = next_event
                return Fixme(["zero-must-occur-only-once"])

            # core: This tick follows its sequence, in either mode.
            case ActivityEvent.TICK, ActivityEvent.ZERO | ActivityEvent.TICK, ActivityEventMode.REGULAR | ActivityEventMode.FALLBACK:
                self.recent_event = next_event
                return Fixme([])

            # core: This tick has no preceding event or follows last, so it does not follow its sequence.
            case ActivityEvent.TICK, None | ActivityEvent.LAST, ActivityEventMode.REGULAR | ActivityEventMode.FALLBACK:
                self.recent_event = next_event
                return Fixme(["tick-must-follow-zero-or-tick"])

            # core: This is the auto-last, but there is one already. Ignore.
            case ActivityEvent.LAST, ActivityEvent.LAST, ActivityEventMode.FALLBACK:
                return None

            # core: No last was logged explicitly. Emit the auto-last with a fixme.
            case ActivityEvent.LAST, None | ActivityEvent.ZERO | ActivityEvent.TICK, ActivityEventMode.FALLBACK:
                self.duration_ms = self.stopwatch.elapsed_ms
                self.recent_event = next_event
                return Fixme(["last-must-be-explicit"])

            # core: This explicit last follows its sequence.
            case ActivityEvent.LAST, ActivityEvent.ZERO | ActivityEvent.TICK, ActivityEventMode.REGULAR:
                self.duration_ms = self.stopwatch.elapsed_ms
                self.recent_event = next_event
                return Fixme([])

            # core: This is another explicit last.
            case ActivityEvent.LAST, ActivityEvent.LAST, ActivityEventMode.REGULAR:
                self.duration_ms = self.stopwatch.elapsed_ms
                self.recent_event = next_event
                return Fixme(["last-must-occur-only-once"])

            # core: This explicit last has no preceding zero or tick.
            case ActivityEvent.LAST, None, ActivityEventMode.REGULAR:
                self.duration_ms = self.stopwatch.elapsed_ms
                self.recent_event = next_event
                return Fixme(["last-must-follow-zero-or-tick"])

            # core: An event, state, or mode combination is missing from the cases above.
            case _:
                raise ValueError(f"Unhandled activity transition: next_event={next_event!r}, recent_event={self.recent_event!r}, mode={mode!r}")

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

    def _log(self, message: str | None, level: int, **kwargs) -> None:

        mode = kwargs.pop("_mode", ActivityEventMode.REGULAR)
        move_result = self._activity.move_next(self._event, mode)

        if move_result is None:
            return

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
            "fixme": move_result.constraints
        }

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
