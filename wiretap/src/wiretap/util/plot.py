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
from typing import Literal, Optional, Any, Iterator, TypeVar, ClassVar

from wiretap.util.stopwatch import Stopwatch

T = TypeVar("T", bound="PlotScope")


class PlotEvent(IntEnum):
    ZERO = auto()
    TICK = auto()
    LAST = auto()
    SNAP = auto()


USER = {"plot.story": "user"}
"""Marks a log entry as part of the application's domain behavior."""

BUZZ = {"plot.story": "buzz"}
"""Marks a log entry as technical or infrastructure-related."""

ZERO = {"plot.event": PlotEvent.ZERO.name.lower()}
TICK = {"plot.event": PlotEvent.TICK.name.lower()}
LAST = {"plot.event": PlotEvent.LAST.name.lower()}


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


class PlotScope:
    """
    This class represents a single plot scope.
    """

    _stack: ClassVar[ContextVar[Optional["PlotScope"]]] = ContextVar("current_plot", default=None)

    def __init__(
            self,
            about: str,
            story: Literal["user", "buzz"],
            state: dict[str, Any],
            trace_id: str | None,
            parent: Optional["PlotScope"] = None,
            parent_id: str | None = None,
    ):
        """
        Initializes a new PlotScope instance.

        Args:
            about: The name of the plot.
            story: The default story for events in this plot.
            state: The initial state of the plot.
            trace_id: The trace ID for the plot.
            parent: The parent plot.
            parent_id: External parent span ID, used when there is no local parent plot.
        """
        self.about = about
        self.story = story
        self.parent = parent
        self.depth: int = parent.depth + 1 if parent else 0
        if parent:
            if trace_id is None:
                trace_id = parent.trace.id
            parent_id = parent.trace.span_id
        self.trace = TraceW3C.create(trace_id=trace_id, parent_id=parent_id)
        self.state: dict = parent.state | state if parent else state

        self.history: list[PlotEvent] = []
        self.stopwatch: Stopwatch = Stopwatch()
        self.duration_ms: int = 0

    def __iter__(self) -> Iterator["PlotScope"]:
        current: Optional["PlotScope"] = self
        while current:
            yield current
            current = current.parent

    # core: Stops the plot-scope so that omitted last events can be detected.
    @classmethod
    @contextlib.contextmanager
    def push(
            cls,
            about: str,
            story: Literal["user", "buzz"],
            state: dict[str, Any],
            trace_id: str | None = None,
            parent_id: str | None = None,
    ) -> Iterator["PlotScope"]:
        """
        Creates and pushes a child of the current plot-scope onto the stack.
        """

        plot = cls(
            about=about,
            story=story,
            state=state,
            trace_id=trace_id,
            parent=cls.get_current(),
            parent_id=parent_id,
        )
        token = cls._stack.set(plot)
        try:
            yield plot
        finally:
            cls._stack.reset(token)

    # note: There is no builtin @classproperty! :-\
    @classmethod
    def get_current(cls) -> Optional["PlotScope"]:
        return cls._stack.get()


class PlotAbout:
    def __init__(self, plot: PlotScope) -> None:
        self._plot = plot

    @property
    def trace(self) -> TraceW3C:
        return self._plot.trace

    @property
    def elapsed_ms(self) -> int:
        return self._plot.stopwatch.elapsed_ms

    @cached_property
    def zero(self) -> ZeroLogger:
        return ZeroLogger(self._plot)

    @cached_property
    def tick(self) -> TickLogger:
        return TickLogger(self._plot)

    @cached_property
    def last(self) -> LastLogger:
        return LastLogger(self._plot)


class EventLogger:
    """Provides the logging methods shared by plot and solo events."""

    def _emit(
            self,
            message: str | None,
            story: Literal["user", "buzz"] | None = None,
            level: int = logging.INFO,
            **kwargs,
    ) -> None:
        raise NotImplementedError

    def log_debug(
            self,
            message: str | None,
            story: Literal["user", "buzz"] | None = None,
            **kwargs,
    ) -> None:
        self._emit(message, story, level=logging.DEBUG, **kwargs)

    def log_info(
            self,
            message: str | None,
            story: Literal["user", "buzz"] | None = None,
            **kwargs,
    ) -> None:
        self._emit(message, story, level=logging.INFO, **kwargs)

    def log_warning(
            self,
            message: str | None,
            story: Literal["user", "buzz"] | None = None,
            **kwargs,
    ) -> None:
        self._emit(message, story, level=logging.WARNING, **kwargs)

    def log_error(
            self,
            message: str | None,
            story: Literal["user", "buzz"] | None = None,
            **kwargs,
    ) -> None:
        self._emit(message, story, level=logging.ERROR, **kwargs)


class PlotEventLogger(EventLogger):
    _event: ClassVar[PlotEvent]

    def __init__(self, plot: PlotScope) -> None:
        self._plot = plot
        self.logger: logging.Logger = logging.getLogger(plot.about)

    def _log(self, data: dict[str, Any]) -> dict[str, Any] | None:
        raise NotImplementedError

    def _emit(
            self,
            message: str | None,
            story: Literal["user", "buzz"] | None = None,
            level: int = logging.INFO,
            **kwargs,
    ) -> None:
        data: dict[str, Any] = {
            "plot": {
                "about": self._plot.about,
                "depth": self._plot.depth,
                "event": self._event.name,
                "story": self._plot.story if story is None else story,
            },
            "fixme": [],
            "aboutme": [],
        }

        if (enriched := self._log(data)) is None:
            return

        # core: Record accepted events even when their log level is filtered out.
        self._plot.history.append(self._event)

        if not self.logger.isEnabledFor(level):
            return

        # mata: Remove it before copying kwargs into the logged context.
        stack_level = kwargs.pop("stack_level", 3)

        context = self._plot.state.copy()
        context.update(kwargs)

        extra: dict[str, Any] = {
            "_wiretap": True,
            "context": context,
            "trace": self._plot.trace.to_dict(),
            **enriched,
        }

        self.logger.log(
            level=level,
            msg=message,
            exc_info=sys.exc_info()[0] is not None,
            extra=extra,
            stacklevel=stack_level,
        )


class ZeroLogger(PlotEventLogger):
    _event = PlotEvent.ZERO

    def _log(self, data: dict[str, Any]) -> dict[str, Any] | None:
        # core: After last, report only that the plot has already ended.
        if PlotEvent.LAST in self._plot.history:
            data["fixme"].append("no-events-must-follow-last")
        else:
            # core: Otherwise, attach the duplicate-zero diagnostic to this zero.
            if PlotEvent.ZERO in self._plot.history:
                data["fixme"].append("zero-occurs-more-than-once")

        return data


class TickLogger(PlotEventLogger):
    # core: Ticks need no sequence validation before the first last.
    _event = PlotEvent.TICK

    def _log(self, data: dict[str, Any]) -> dict[str, Any] | None:
        # core: Ticks are unrestricted until the plot has ended.
        if PlotEvent.LAST in self._plot.history:
            data["fixme"].append("no-events-must-follow-last")

        return data


class LastLogger(PlotEventLogger):
    _event = PlotEvent.LAST

    def __init__(self, plot: PlotScope, *, _once: bool = False) -> None:
        super().__init__(plot)
        self._once = _once

    @cached_property
    def once(self) -> LastLogger:
        return LastLogger(self._plot, _once=True)

    def _log(self, data: dict[str, Any]) -> dict[str, Any] | None:
        if PlotEvent.LAST in self._plot.history:
            # core: Scope closure does not add another last if one already occurred.
            if self._once:
                return None

            # core: A repeated explicit last is logged without changing the duration.
            data["plot"]["duration_ms"] = self._plot.duration_ms
            data["fixme"].append("no-events-must-follow-last")
            return data

        # core: Only the first last reports omissions and captures the plot's duration.
        if PlotEvent.ZERO not in self._plot.history:
            data["aboutme"].append("does-not-log-zero")

        if self._once:
            data["aboutme"].append("logs-last-silently")

        self._plot.duration_ms = self._plot.stopwatch.elapsed_ms
        data["plot"]["duration_ms"] = self._plot.duration_ms
        return data


class SnapLogger(EventLogger):
    """Emits the snap event"""

    def __init__(self, about: str, story: Literal["user", "buzz"]) -> None:
        self.about = about
        self.story = story
        self._logger: logging.Logger = logging.getLogger(about)

    def _emit(
            self,
            message: str | None,
            story: Literal["user", "buzz"] | None = None,
            level: int = logging.INFO,
            **kwargs,
    ) -> None:
        if not self._logger.isEnabledFor(level):
            return

        stack_level = kwargs.pop("stack_level", 3)
        plot = PlotScope.get_current()
        context = plot.state.copy() if plot else {}
        context.update(kwargs)

        self._logger.log(
            level=level,
            msg=message,
            exc_info=sys.exc_info()[0] is not None,
            extra={
                "_wiretap": True,
                "plot": {
                    "about": self.about,
                    "event": PlotEvent.SNAP.name,
                    "story": self.story if story is None else story,
                    "depth": plot.depth + 1 if plot else 0,
                },
                "context": context,
                "trace": plot.trace.to_dict() if plot else None,
            },
            stacklevel=stack_level,
        )
