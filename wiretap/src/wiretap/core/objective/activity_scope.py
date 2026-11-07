from __future__ import annotations

import contextlib
import logging
from contextvars import ContextVar
from typing import Any, ClassVar, Iterator, Optional

from wiretap.util import Focus
from wiretap.util.activity_event import ActivityEvent
from wiretap.util.stopwatch import Stopwatch
from wiretap.util.trace_w3c import TraceW3C


class ActivityScope:
    """
    This class represents a single activity.
    """

    _stack: ClassVar[ContextVar[Optional["ActivityScope"]]] = ContextVar("current_activity", default=None)

    def __init__(
            self,
            logger: logging.Logger,
            about: str,
            focus: Focus,
            state: dict[str, Any],
            trace_id: str | None,
            parent: Optional["ActivityScope"] = None,
            parent_id: str | None = None,
    ):
        """
        Initializes a new ActivityScope instance.

        Args:
            logger: The logger used for diagnostic longs.
            about: The name of the activity.
            focus: The focus for events in this activity.
            state: The initial state of the activity.
            trace_id: The trace ID for the activity.
            parent: The parent activity.
            parent_id: External parent span ID, taking precedence over the local parent span ID.
        """
        self.logger = logger
        self.about = about
        self.focus = focus
        self.parent = parent
        self.depth: int = parent.depth + 1 if parent else 0
        resolved_trace_id = trace_id
        resolved_parent_id = parent_id
        if parent:
            if resolved_trace_id is None:
                resolved_trace_id = parent.trace.id
            if resolved_parent_id is None:
                resolved_parent_id = parent.trace.span_id
        self.trace: TraceW3C = TraceW3C.create(trace_id=resolved_trace_id, parent_id=resolved_parent_id)
        self.state: dict[str, Any] = parent.state | state if parent else state.copy()

        self.history: list[ActivityEvent] = []
        self.beeps: set[str] = set()
        self.stopwatch: Stopwatch = Stopwatch()
        self.duration_ms: int = 0

    def extra(
            self,
            event: ActivityEvent,
            focus: Focus | None = None,
            **kwargs,
    ) -> dict[str, Any]:
        """
        Creates extra with default values.
        """

        return {
            "_format_map": True,
            "activity": {
                "about": self.about,
                "event": event.name,
                "focus": self.focus if focus is None else focus,
                "depth": self.depth,
            },
            "properties": self.state | kwargs,
            "trace": self.trace.to_dict(),
        }

    def beep(
            self,
            level: int,
            message: str | None,
            beep_code: str,
            stacklevel: int = 3,
            **kwargs,
    ) -> None:
        """
        Logs diagnostic messages.
        """

        if beep_code in self.beeps or not self.logger.isEnabledFor(level):
            return

        extra = self.extra(ActivityEvent.BEEP, "buzz", **kwargs)
        extra["properties"]["beep_code"] = beep_code
        self.beeps.add(beep_code)
        self.logger.log(level, message, extra=extra, stacklevel=stacklevel)

    def __iter__(self) -> Iterator["ActivityScope"]:
        current: Optional["ActivityScope"] = self
        while current:
            yield current
            current = current.parent

    # core: Restore the previous activity even when activity handling raises.
    @classmethod
    @contextlib.contextmanager
    def push(
            cls,
            logger: logging.Logger,
            about: str,
            focus: Focus,
            state: dict[str, Any],
            trace_id: str | None = None,
            parent_id: str | None = None,
    ) -> Iterator["ActivityScope"]:
        """
        Creates and pushes a child of the current activity onto the stack.
        """

        activity = cls(
            logger=logger,
            about=about,
            focus=focus,
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
