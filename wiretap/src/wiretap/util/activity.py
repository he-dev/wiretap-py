from __future__ import annotations
import contextlib
import logging
import re
import secrets
import sys
from contextvars import ContextVar  # noqa: built-in module
from dataclasses import dataclass
from enum import auto, IntEnum
from functools import cached_property
from typing import Optional, Any, Iterator, TypeVar, ClassVar

from wiretap.util.stopwatch import Stopwatch

T = TypeVar("T", bound="ActivityScope")


class ActivityEvent(IntEnum):
    ZERO = auto()
    TICK = auto()
    LAST = auto()


DOMAIN = {"story": "domain"}
"""Marks a log entry as part of the application's domain behavior."""

SYSTEM = {"story": "system"}
"""Marks a log entry as technical or infrastructure-related."""

ZERO = {"activity.event": ActivityEvent.ZERO.name.lower()}
TICK = {"activity.event": ActivityEvent.TICK.name.lower()}
LAST = {"activity.event": ActivityEvent.LAST.name.lower()}


@dataclass(frozen=True)
class TraceW3C:
    id: str
    span_id: str
    parent_id: str | None

    @classmethod
    def create(
            cls,
            trace_id: str | None = None,
            parent_id: str | None = None,
    ) -> TraceW3C:
        if trace_id is None:
            trace_id = cls._generate_id(16)
        else:
            cls._validate_id(trace_id, 32, "trace_id")

        if parent_id is not None:
            cls._validate_id(parent_id, 16, "parent_id")

        return cls(id=trace_id, span_id=cls._generate_id(8), parent_id=parent_id)

    @staticmethod
    def _validate_id(value: str, length: int, name: str) -> None:
        if not isinstance(value, str) or re.fullmatch(rf"[0-9a-f]{{{length}}}", value) is None:
            raise ValueError(f"{name} must be {length} lowercase hex characters")
        if value == "0" * length:
            raise ValueError(f"{name} must not be all zeros")

    @staticmethod
    def _generate_id(size: int) -> str:
        zero = "0" * (size * 2)
        value = secrets.token_hex(size)
        while value == zero:
            value = secrets.token_hex(size)
        return value

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
        }


class ActivityScope:
    """
    This class represents a single activity scope.
    """

    _stack: ClassVar[ContextVar[Optional["ActivityScope"]]] = ContextVar("current_activity", default=None)

    def __init__(
            self,
            about: str,
            state: dict[str, Any],
            trace_id: str | None,
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
        self.depth: int = parent.depth + 1 if parent else 0
        if parent:
            if trace_id is None:
                trace_id = parent.trace.id
            parent_id = parent.trace.span_id
        self.trace = TraceW3C.create(trace_id=trace_id, parent_id=parent_id)
        self.state: dict = parent.state | state if parent else state

        self.history: list[ActivityEvent] = []
        self.stopwatch: Stopwatch = Stopwatch()
        self.duration_ms: int = 0

    def __iter__(self) -> Iterator["ActivityScope"]:
        current: Optional["ActivityScope"] = self
        while current:
            yield current
            current = current.parent

    # core: Stops the activity-scope so that omitted last events can be detected.
    @classmethod
    @contextlib.contextmanager
    def push(
            cls,
            about: str,
            state: dict[str, Any],
            trace_id: str | None = None,
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
    def trace(self) -> TraceW3C:
        return self._activity.trace

    @property
    def elapsed_ms(self) -> int:
        return self._activity.stopwatch.elapsed_ms

    @cached_property
    def zero(self) -> ZeroLogger:
        return ZeroLogger(self._activity)

    @cached_property
    def tick(self) -> TickLogger:
        return TickLogger(self._activity)

    @cached_property
    def last(self) -> LastLogger:
        return LastLogger(self._activity)


class EventLogger:
    """Builds and emits records enriched by the individual event loggers."""

    _event: ClassVar[ActivityEvent]

    def __init__(self, activity: ActivityScope) -> None:
        self._activity = activity
        self.logger: logging.Logger = logging.getLogger(activity.about)

    def _log(self, data: dict[str, Any]) -> dict[str, Any] | None:
        raise NotImplementedError

    def _emit(self, message: str | None, level: int, **kwargs) -> None:
        data: dict[str, Any] = {
            "activity": {
                "about": self._activity.about,
                "depth": self._activity.depth,
                "event": self._event.name,
            },
            "fixme": [],
            "aboutme": [],
        }

        if (enriched := self._log(data)) is None:
            return

        # core: Record accepted events even when their log level is filtered out.
        self._activity.history.append(self._event)

        if not self.logger.isEnabledFor(level):
            return

        # mata: Remove it before copying kwargs into the logged context.
        stack_level = kwargs.pop("stack_level", 3)

        context = self._activity.state.copy()
        context.update(kwargs)

        extra: dict[str, Any] = {
            "_wiretap": True,
            "context": context,
            "trace": self._activity.trace.to_dict(),
            **enriched,
        }

        self.logger.log(
            level=level,
            msg=message,
            exc_info=sys.exc_info()[0] is not None,
            extra=extra,
            stacklevel=stack_level,
        )

    def log_debug(self, message: str | None, **kwargs) -> None:
        self._emit(message, logging.DEBUG, **kwargs)

    def log_info(self, message: str | None, **kwargs) -> None:
        self._emit(message, logging.INFO, **kwargs)

    def log_warning(self, message: str | None, **kwargs) -> None:
        self._emit(message, logging.WARNING, **kwargs)

    def log_error(self, message: str | None, **kwargs) -> None:
        self._emit(message, logging.ERROR, **kwargs)


class ZeroLogger(EventLogger):
    _event = ActivityEvent.ZERO

    def _log(self, data: dict[str, Any]) -> dict[str, Any] | None:
        # core: After last, report only that the activity has already ended.
        if ActivityEvent.LAST in self._activity.history:
            data["fixme"].append("no-events-must-follow-last")
        else:
            # core: Otherwise, attach the duplicate-zero diagnostic to this zero.
            if ActivityEvent.ZERO in self._activity.history:
                data["fixme"].append("zero-occurs-more-than-once")

        return data


class TickLogger(EventLogger):
    # core: Ticks need no sequence validation before the first last.
    _event = ActivityEvent.TICK

    def _log(self, data: dict[str, Any]) -> dict[str, Any] | None:
        # core: Ticks are unrestricted until the activity has ended.
        if ActivityEvent.LAST in self._activity.history:
            data["fixme"].append("no-events-must-follow-last")

        return data


class LastLogger(EventLogger):
    _event = ActivityEvent.LAST

    def __init__(self, activity: ActivityScope, *, _once: bool = False) -> None:
        super().__init__(activity)
        self._once = _once

    @cached_property
    def once(self) -> LastLogger:
        return LastLogger(self._activity, _once=True)

    def _log(self, data: dict[str, Any]) -> dict[str, Any] | None:
        if ActivityEvent.LAST in self._activity.history:
            # core: Scope closure does not add another last if one already occurred.
            if self._once:
                return None

            # core: A repeated explicit last is logged without changing the duration.
            data["activity"]["duration_ms"] = self._activity.duration_ms
            data["fixme"].append("no-events-must-follow-last")
            return data

        # core: Only the first last reports omissions and captures the activity's duration.
        if ActivityEvent.ZERO not in self._activity.history:
            data["aboutme"].append("does-not-log-zero")

        if self._once:
            data["aboutme"].append("logs-last-silently")

        self._activity.duration_ms = self._activity.stopwatch.elapsed_ms
        data["activity"]["duration_ms"] = self._activity.duration_ms
        return data
