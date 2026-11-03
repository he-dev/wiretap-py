import contextlib
from typing import Any, Iterator

from wiretap.util.activity import ActivityAbout, ActivityScope


@contextlib.contextmanager
def begin_scope(
        about: str,
        state: dict[str, Any] | None = None,
        trace_id: str | None = None,
        parent_id: str | None = None,
        **kwargs
) -> Iterator[ActivityAbout]:
    """
    Creates an activity scope and logs a closing event if no explicit last event occurred.

    Args:
        about: The name of the span. If None, the name will be derived from the calling frame. Usually the function name.
        state: A dictionary of extra data to log that is attached to each trace.
        trace_id: The trace ID to use for the span. If None, a random ID will be generated.
        parent_id: External parent span ID, used when there is no local parent activity.
        kwargs: Additional keyword arguments to be passed to each trace.

    Returns:
        The newly created span.
    """

    with ActivityScope.push(
            about=about,
            state=(state or {}) | kwargs,
            trace_id=trace_id,
            parent_id=parent_id,
    ) as activity:
        activity_about = ActivityAbout(activity)
        try:
            yield activity_about
        except Exception:
            activity_about.last.once.log_error(
                message="{activity[about]} fails after {activity[duration_ms]} ms.",
                stack_level=5,
                **kwargs
            )
            raise
        else:
            activity_about.last.once.log_info(
                message="{activity[about]} completes in {activity[duration_ms]} ms.",
                stack_level=5,
                **kwargs
            )
