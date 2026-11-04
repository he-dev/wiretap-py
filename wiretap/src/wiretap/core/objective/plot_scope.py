from __future__ import annotations

import contextlib
from contextvars import ContextVar
from typing import Any, ClassVar, Iterator, Literal, Optional

from wiretap.util.plot_event import PlotEvent
from wiretap.util.stopwatch import Stopwatch
from wiretap.util.trace_w3c import TraceW3C


class PlotScope:
    """
    This class represents a single plot scope.
    """

    _stack: ClassVar[ContextVar[Optional["PlotScope"]]] = ContextVar("current_plot", default=None)

    def __init__(
            self,
            about: str,
            story: Literal["core", "buzz"],
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
            parent_id: External parent span ID, taking precedence over the local parent span ID.
        """
        self.about = about
        self.story = story
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

        self.history: list[PlotEvent] = []
        self.stopwatch: Stopwatch = Stopwatch()
        self.duration_ms: int = 0

    def __iter__(self) -> Iterator["PlotScope"]:
        current: Optional["PlotScope"] = self
        while current:
            yield current
            current = current.parent

    # core: Restore the previous scope even when plot handling raises.
    @classmethod
    @contextlib.contextmanager
    def push(
            cls,
            about: str,
            story: Literal["core", "buzz"],
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
