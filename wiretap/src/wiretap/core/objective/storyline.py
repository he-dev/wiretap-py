from __future__ import annotations

import contextlib
import logging
from typing import Any, Iterator, Literal

from wiretap.core.objective.plot import Plot
from wiretap.core.objective.plot_scope import PlotScope
from wiretap.util.plot_event import PlotEvent


class Storyline:
    """Binds a logger to plot scopes and builds standalone snap metadata."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    @classmethod
    def logger(cls, name: str) -> tuple[logging.Logger, Storyline]:
        logger = logging.getLogger(name)
        return logger, cls(logger)

    @contextlib.contextmanager
    def begin_plot(
            self,
            about: str,
            story: Literal["core", "buzz"],
            trace_id: str | None = None,
            parent_id: str | None = None,
            **kwargs,
    ) -> Iterator[Plot]:
        with PlotScope.push(
                logger=self._logger,
                about=about,
                story=story,
                state=kwargs,
                trace_id=trace_id,
                parent_id=parent_id,
        ) as scope:
            plot = Plot(scope)
            error: BaseException | None = None
            try:
                yield plot
            except BaseException as exception:
                error = exception
                raise
            finally:
                if PlotEvent.LAST not in scope.history:
                    extra = plot.last()
                    scope.beep("logs-last-silently", logging.DEBUG, {}, stack_level=4)
                    level = logging.INFO
                    message = "{plot[about]} completes in {plot[duration_ms]} ms."
                    if error is not None:
                        level = logging.ERROR
                        message = "{plot[about]} fails after {plot[duration_ms]} ms."
                    self._logger.log(
                        level=level,
                        msg=message,
                        extra=extra,
                        exc_info=error is not None,
                        stacklevel=3,
                    )

    def snap(self, about: str, story: Literal["core", "buzz"], **kwargs) -> dict[str, Any]:
        scope = PlotScope.get_current()
        context = scope.state.copy() if scope else {}
        context.update(kwargs)
        return {
            "_format_map": True,
            "plot": {
                "about": about,
                "event": PlotEvent.SNAP.name,
                "story": story,
                "depth": scope.depth + 1 if scope else 0,
            },
            "context": context,
            "trace": scope.trace.to_dict() if scope else None,
        }
