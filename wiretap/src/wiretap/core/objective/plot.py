from __future__ import annotations

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
        extra = self._extra(PlotEvent.ZERO, story, kwargs)
        if PlotEvent.LAST in self._scope.history:
            extra["plot"]["diagnostics"]["errors"].append("no-events-must-follow-last")
        if PlotEvent.ZERO in self._scope.history:
            extra["plot"]["diagnostics"]["errors"].append("zero-occurs-more-than-once")
        self._scope.history.append(PlotEvent.ZERO)
        return extra

    def tick(self, story: Literal["core", "buzz"] | None = None, **kwargs) -> dict[str, Any]:
        extra = self._extra(PlotEvent.TICK, story, kwargs)
        if PlotEvent.LAST in self._scope.history:
            extra["plot"]["diagnostics"]["errors"].append("no-events-must-follow-last")
        self._scope.history.append(PlotEvent.TICK)
        return extra

    def last(self, story: Literal["core", "buzz"] | None = None, **kwargs) -> dict[str, Any]:
        extra = self._extra(PlotEvent.LAST, story, kwargs)
        if PlotEvent.LAST in self._scope.history:
            extra["plot"]["diagnostics"]["errors"].append("no-events-must-follow-last")
        else:
            if PlotEvent.ZERO not in self._scope.history:
                extra["plot"]["diagnostics"]["remarks"].append("does-not-log-zero")
            self._scope.duration_ms = self._scope.stopwatch.elapsed_ms
        extra["plot"]["duration_ms"] = self._scope.duration_ms
        self._scope.history.append(PlotEvent.LAST)
        return extra

    def _extra(self, event: PlotEvent, story: Literal["core", "buzz"] | None, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "_format_map": True,
            "plot": {
                "about": self._scope.about,
                "event": event.name,
                "story": self._scope.story if story is None else story,
                "depth": self._scope.depth,
                "diagnostics": {
                    "errors": [],
                    "remarks": [],
                },
            },
            "context": self._scope.state | context,
            "trace": self._scope.trace.to_dict(),
        }
