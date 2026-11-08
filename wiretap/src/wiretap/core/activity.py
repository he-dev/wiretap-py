from __future__ import annotations

import logging
from typing import Any

from wiretap.core.activity_scope import ActivityScope
from wiretap.core.activity_event import ActivityEvent
from wiretap.util.trace_w3c import TraceW3C


class Activity:
    """
    Provides event extra.
    """

    def __init__(self, activity: ActivityScope) -> None:
        self._activity = activity

    @property
    def trace(self) -> TraceW3C:
        return self._activity.trace

    @property
    def elapsed_ms(self) -> int:
        return self._activity.stopwatch.elapsed_ms

    def zero(self, channel: str | None = None, **kwargs) -> dict[str, Any]:
        extra = self._activity.extra(ActivityEvent.ZERO, channel, **kwargs)

        if ActivityEvent.LAST in self._activity.history:
            self._activity.beep(
                logging.ERROR,
                "Activity {activity[about]} logs ZERO after LAST.",
                "no-events-must-follow-last",
                **kwargs,
            )

        if ActivityEvent.ZERO in self._activity.history:
            self._activity.beep(
                logging.ERROR,
                "Activity {activity[about]} logs ZERO more than once.",
                "zero-occurs-more-than-once",
                **kwargs,
            )

        if ActivityEvent.TICK in self._activity.history:
            self._activity.beep(
                logging.ERROR,
                "Activity {activity[about]} logs ZERO after TICK.",
                "zero-must-precede-tick",
                **kwargs,
            )

        self._activity.history.append(ActivityEvent.ZERO)
        return extra

    def tick(self, channel: str | None = None, **kwargs) -> dict[str, Any]:
        extra = self._activity.extra(ActivityEvent.TICK, channel, **kwargs)

        if ActivityEvent.LAST in self._activity.history:
            self._activity.beep(
                logging.ERROR,
                "Activity {activity[about]} logs TICK after LAST.",
                "no-events-must-follow-last",
                **kwargs,
            )

        self._activity.history.append(ActivityEvent.TICK)
        return extra

    def last(self, channel: str | None = None, **kwargs) -> dict[str, Any]:
        extra = self._activity.extra(ActivityEvent.LAST, channel, **kwargs)

        if ActivityEvent.LAST in self._activity.history:
            self._activity.beep(
                logging.ERROR,
                "Activity {activity[about]} logs LAST more than once.",
                "no-events-must-follow-last",
                **kwargs,
            )
        else:
            if ActivityEvent.ZERO not in self._activity.history:
                self._activity.beep(
                    logging.DEBUG,
                    "Activity {activity[about]} reaches LAST without ZERO.",
                    "does-not-log-zero",
                    **kwargs,
                )
            self._activity.duration_ms = self._activity.stopwatch.elapsed_ms

        extra["activity"]["duration_ms"] = self._activity.duration_ms
        self._activity.history.append(ActivityEvent.LAST)
        return extra
