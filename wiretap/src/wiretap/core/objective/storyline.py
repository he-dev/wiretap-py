from __future__ import annotations

import contextlib
import logging
import logging.config
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

    @staticmethod
    def configure(config: dict):
        """
        Configures standard Python logging.
        """
        logging.config.dictConfig(config)

    @contextlib.contextmanager
    def begin_plot(
            self,
            about: str,
            story: Literal["core", "buzz"],
            trace_id: str | None = None,
            parent_id: str | None = None,
            **kwargs,
    ) -> Iterator[Plot]:
        """
        Begins a new plot.
        """

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
                    scope.beep(
                        logging.DEBUG,
                        "Plot {plot[about]} ends without an explicit LAST.",
                        "logs-last-silently",
                        stacklevel=4,
                    )
                    level = logging.INFO
                    message = "Plot {plot[about]} completes in {plot[duration_ms]} ms."
                    if error is not None:
                        level = logging.ERROR
                        message = "Plot {plot[about]} fails after {plot[duration_ms]} ms."
                    self._logger.log(
                        level=level,
                        msg=message,
                        extra=extra,
                        exc_info=error is not None,
                        stacklevel=3,
                    )

    def snap(self, about: str, story: Literal["core", "buzz"], **kwargs) -> dict[str, Any]:
        scope = PlotScope.get_current()
        sample = scope.state.copy() if scope else {}
        sample.update(kwargs)
        return {
            "_format_map": True,
            "plot": {
                "about": about,
                "event": PlotEvent.SNAP.name,
                "story": story,
                "depth": scope.depth + 1 if scope else 0,
            },
            "sample": sample,
            "trace": scope.trace.to_dict() if scope else None,
        }
