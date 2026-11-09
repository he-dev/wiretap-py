from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from wiretap.core.activity_scope import ActivityScope
from wiretap.core.activity_event import ActivityEvent
from wiretap.util.trace_w3c import TraceW3C
from wiretap.util.buzz.merge_properties import merge_properties


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
        return self._activity.stopwatch.elapsed.duration_ms

    def zero(self, *args: Mapping[str, Any], channel: str | None = None, **kwargs: Any) -> dict[str, Any]:
        kwargs = merge_properties(*args, **kwargs)
        if channel is not None:
            kwargs["channel"] = channel
        extra = self._activity.extra(ActivityEvent.ZERO, **kwargs)

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

    def tick(self, *args: Mapping[str, Any], channel: str | None = None, **kwargs: Any) -> dict[str, Any]:
        kwargs = merge_properties(*args, **kwargs)
        if channel is not None:
            kwargs["channel"] = channel
        extra = self._activity.extra(ActivityEvent.TICK, **kwargs)

        if ActivityEvent.LAST in self._activity.history:
            self._activity.beep(
                logging.ERROR,
                "Activity {activity[about]} logs TICK after LAST.",
                "no-events-must-follow-last",
                **kwargs,
            )

        self._activity.history.append(ActivityEvent.TICK)
        return extra

    def last(self, *args: Mapping[str, Any], channel: str | None = None, **kwargs: Any) -> dict[str, Any]:
        kwargs = merge_properties(*args, **kwargs)
        if channel is not None:
            kwargs["channel"] = channel
        extra = self._activity.extra(ActivityEvent.LAST, **kwargs)

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
            self._activity.duration_ms = self._activity.stopwatch.elapsed.duration_ms

        extra["activity"]["duration_ms"] = self._activity.duration_ms
        self._activity.history.append(ActivityEvent.LAST)
        return extra
