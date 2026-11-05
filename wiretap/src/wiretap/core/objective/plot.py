from __future__ import annotations

import logging
from typing import Any, Literal

from wiretap.core.objective.plot_scope import PlotScope
from wiretap.util.plot_event import PlotEvent
from wiretap.util.trace_w3c import TraceW3C


class Plot:
    """
    Provides event extra.
    """

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
            self._scope.beep(
                logging.ERROR,
                "Plot {plot[about]} logs ZERO after LAST.",
                "no-events-must-follow-last",
                **kwargs,
            )

        if PlotEvent.ZERO in self._scope.history:
            self._scope.beep(
                logging.ERROR,
                "Plot {plot[about]} logs ZERO more than once.",
                "zero-occurs-more-than-once",
                **kwargs,
            )

        if PlotEvent.TICK in self._scope.history:
            self._scope.beep(
                logging.ERROR,
                "Plot {plot[about]} logs ZERO after TICK.",
                "zero-must-precede-tick",
                **kwargs,
            )

        self._scope.history.append(PlotEvent.ZERO)
        return extra

    def tick(self, story: Literal["core", "buzz"] | None = None, **kwargs) -> dict[str, Any]:
        extra = self._scope.extra(PlotEvent.TICK, story, **kwargs)

        if PlotEvent.LAST in self._scope.history:
            self._scope.beep(
                logging.ERROR,
                "Plot {plot[about]} logs TICK after LAST.",
                "no-events-must-follow-last",
                **kwargs,
            )

        self._scope.history.append(PlotEvent.TICK)
        return extra

    def last(self, story: Literal["core", "buzz"] | None = None, **kwargs) -> dict[str, Any]:
        extra = self._scope.extra(PlotEvent.LAST, story, **kwargs)

        if PlotEvent.LAST in self._scope.history:
            self._scope.beep(
                logging.ERROR,
                "Plot {plot[about]} logs LAST more than once.",
                "no-events-must-follow-last",
                **kwargs,
            )
        else:
            if PlotEvent.ZERO not in self._scope.history:
                self._scope.beep(
                    logging.DEBUG,
                    "Plot {plot[about]} reaches LAST without ZERO.",
                    "does-not-log-zero",
                    **kwargs,
                )
            self._scope.duration_ms = self._scope.stopwatch.elapsed_ms

        extra["plot"]["duration_ms"] = self._scope.duration_ms
        self._scope.history.append(PlotEvent.LAST)
        return extra
