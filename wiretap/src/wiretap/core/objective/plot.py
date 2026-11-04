from __future__ import annotations

import logging
from typing import Any, Literal

from wiretap.core.objective.plot_scope import PlotScope
from wiretap.util.plot_event import PlotEvent
from wiretap.util.trace_w3c import TraceW3C


class Plot:
    """Builds event metadata using lifecycle state owned by its scope."""

    def __init__(self, scope: PlotScope) -> None:
        self._scope = scope

    @property
    def trace(self) -> TraceW3C:
        return self._scope.trace

    @property
    def elapsed_ms(self) -> int:
        return self._scope.stopwatch.elapsed_ms

    def zero(self, story: Literal["core", "buzz"] | None = None, **kwargs) -> dict[str, Any]:
        extra = self._scope.extra(PlotEvent.ZERO, story, **kwargs)

        if PlotEvent.LAST in self._scope.history:
            self._scope.beep("no-events-must-follow-last", logging.ERROR, kwargs)

        if PlotEvent.ZERO in self._scope.history:
            self._scope.beep("zero-occurs-more-than-once", logging.ERROR, kwargs)

        if PlotEvent.TICK in self._scope.history:
            self._scope.beep("zero-must-precede-tick", logging.ERROR, kwargs)

        self._scope.history.append(PlotEvent.ZERO)
        return extra

    def tick(self, story: Literal["core", "buzz"] | None = None, **kwargs) -> dict[str, Any]:
        extra = self._scope.extra(PlotEvent.TICK, story, **kwargs)

        if PlotEvent.LAST in self._scope.history:
            self._scope.beep("no-events-must-follow-last", logging.ERROR, kwargs)

        self._scope.history.append(PlotEvent.TICK)
        return extra

    def last(self, story: Literal["core", "buzz"] | None = None, **kwargs) -> dict[str, Any]:
        extra = self._scope.extra(PlotEvent.LAST, story, **kwargs)

        if PlotEvent.LAST in self._scope.history:
            self._scope.beep("no-events-must-follow-last", logging.ERROR, kwargs)
        else:
            if PlotEvent.ZERO not in self._scope.history:
                self._scope.beep("does-not-log-zero", logging.DEBUG, kwargs)
            self._scope.duration_ms = self._scope.stopwatch.elapsed_ms

        extra["plot"]["duration_ms"] = self._scope.duration_ms
        self._scope.history.append(PlotEvent.LAST)
        return extra
