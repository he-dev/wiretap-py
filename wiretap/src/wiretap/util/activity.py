import contextlib
import inspect
import logging
import secrets
import sys
from contextvars import ContextVar  # noqa: built-in module
from enum import Enum, auto
from types import FrameType
from typing import Optional, Any, Iterator, TypeVar, ClassVar, Protocol

from wiretap.meta import trim_path
from wiretap.util.stopwatch import Stopwatch

T = TypeVar("T", bound="ActivityScope")


class ActivityEvent(Enum):
    ZERO = auto()
    TICK = auto()
    LAST = auto()


DOMAIN = {"story": "domain"}
SYSTEM = {"story": "system"}
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
    ):
        """
        Initializes a new ActivityScope instance.

        Args:
            about: The name of the activity.
            state: The initial state of the activity.
            trace_id: The trace ID for the activity.
            parent: The parent activity.
        """
        self.about = about
        self.parent = parent
        self.trace_id: str = trace_id or (parent.trace_id if parent else secrets.token_hex(16))
        self.span_id: str = secrets.token_hex(8)
        self.state = parent.state | state if parent else state
        self.recent_event: Optional[ActivityEvent] = None
        self.stopwatch: Stopwatch = Stopwatch()
        self.duration_ms: int = 0

    def __iter__(self) -> Iterator["ActivityScope"]:
        current: Optional["ActivityScope"] = self
        while current:
            yield current
            current = current.parent

    @property
    def depth(self) -> int:
        return self.parent.depth + 1 if self.parent else 0

    def move_next(self, next_event: ActivityEvent) -> dict:

        activity = {}

        match next_event:
            case ActivityEvent.ZERO if self.recent_event is None:
                self.recent_event = next_event
                self.stopwatch = Stopwatch()
                pass
            case ActivityEvent.TICK if self.recent_event == ActivityEvent.ZERO or self.recent_event == ActivityEvent.TICK:
                self.recent_event = next_event
            case ActivityEvent.LAST if self.recent_event == ActivityEvent.TICK:
                self.recent_event = next_event
                self.duration_ms = self.stopwatch.elapsed_ms
            case _:
                # core: The requested transition from one event to the next is not valid.
                activity = activity | {
                    "issue": "InvalidEventOrder"
                }

        activity = activity | {
            "about": self.about,
            "event": next_event.name,
            "depth": self.depth,
        }

        match next_event:
            case ActivityEvent.LAST:
                activity = activity | {
                    "duration_ms": self.duration_ms
                }

        return {"context": self.state} | {
            "activity": activity
        } | {
            "trace": {
                "id": self.trace_id,
                "span_id": self.span_id,
                "parent_id": self.parent.span_id if self.parent else None
            }
        }

    @contextlib.contextmanager
    def push(self) -> Iterator["ActivityScope"]:
        """
        Pushes the current span onto the stack.
        """

        token = ActivityScope._stack.set(self)
        try:
            yield self
        finally:
            ActivityScope._stack.reset(token)

    # note: There is no builtin @classproperty! :-\
    @classmethod
    def get_current(cls) -> Optional["ActivityScope"]:
        return cls._stack.get()


class ActivityAbout:
    def __init__(self, activity: ActivityScope) -> None:
        self._activity = activity

    @property
    def zero(self) -> ActivityLogger:
        return ActivityLogger(self._activity, ActivityEvent.ZERO)

    @property
    def tick(self) -> ActivityLogger:
        return ActivityLogger(self._activity, ActivityEvent.TICK)

    @property
    def last(self) -> ActivityLogger:
        return ActivityLogger(self._activity, ActivityEvent.LAST)


class ActivityLogger:
    def __init__(self, activity: ActivityScope, event: ActivityEvent) -> None:
        self._activity = activity
        self._event = event
        self.logger: logging.Logger = logging.getLogger(activity.about)

    def _log_event(
            self,
            message: str | None,
            level: int,
            event: ActivityEvent,
            **kwargs
    ) -> None:
        extra = kwargs | self._activity.move_next(event)

        self.logger.log(
            level=level,
            msg=message,
            exc_info=level >= logging.ERROR or sys.exc_info()[0] is not None,
            extra=extra | {"_wiretap": True},
            stacklevel=3
        )

    def log_debug(self, message: str | None, **kwargs) -> None:
        self._log_event(message, logging.DEBUG, self._event, **kwargs)

    def log_info(self, message: str | None, **kwargs) -> None:
        self._log_event(message, logging.INFO, self._event, **kwargs)

    def log_warning(self, message: str | None, **kwargs) -> None:
        self._log_event(message, logging.WARNING, self._event, **kwargs)

    def log_error(self, message: str | None, **kwargs) -> None:
        self._log_event(message, logging.ERROR, self._event, **kwargs)
