from __future__ import annotations

import contextlib
import logging
import logging.config
from typing import Any, Iterator

from wiretap.core.activity import Activity
from wiretap.core.activity_scope import ActivityScope
from wiretap.core.activity_event import ActivityEvent


class Wiretap:
    """Binds a logger to activities and builds standalone snap metadata."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    @classmethod
    def get(cls: type[Wiretap], name: str) -> tuple[logging.Logger, Wiretap]:
        logger = logging.getLogger(name)
        return logger, cls(logger)

    @staticmethod
    def configure(config: dict):
        """
        Configures standard Python logging.
        """
        logging.config.dictConfig(config)

    @contextlib.contextmanager
    def begin_scope(
            self,
            about: str,
            channel: str,
            trace_id: str | None = None,
            parent_id: str | None = None,
            **kwargs,
    ) -> Iterator[Activity]:
        """
        Begins a new activity.
        """

        with ActivityScope.push(
                logger=self._logger,
                about=about,
                channel=channel,
                state=kwargs,
                trace_id=trace_id,
                parent_id=parent_id,
        ) as activity_scope:
            activity = Activity(activity_scope)
            error: BaseException | None = None
            try:
                yield activity
            except BaseException as exception:
                error = exception
                raise
            finally:
                if ActivityEvent.LAST not in activity_scope.history:
                    extra = activity.last()
                    activity_scope.beep(
                        logging.DEBUG,
                        "Activity {activity[about]} ends without an explicit LAST.",
                        "logs-last-silently",
                        stacklevel=4,
                    )
                    level = logging.INFO
                    message = "Activity {activity[about]} completes in {activity[duration_ms]:,d} ms."
                    if error is not None:
                        level = logging.ERROR
                        message = "Activity {activity[about]} fails after {activity[duration_ms]:,d} ms."
                    self._logger.log(
                        level=level,
                        msg=message,
                        extra=extra,
                        exc_info=error is not None,
                        stacklevel=3,
                    )

    def snap(self, about: str, channel: str, **kwargs) -> dict[str, Any]:
        activity = ActivityScope.get_current()
        properties = activity.state.copy() if activity else {}
        properties.update(kwargs)
        return {
            "_format_map": True,
            "activity": {
                "about": about,
                "event": ActivityEvent.SNAP.name,
                "channel": channel,
                "depth": activity.depth + 1 if activity else 0,
            },
            "properties": properties,
            "trace": activity.trace.to_dict() if activity else None,
        }
