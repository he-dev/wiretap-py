import contextlib
from typing import Any, Iterator

from wiretap.util.activity import ActivityAbout, ActivityScope


@contextlib.contextmanager
def begin_scope(
        about: str,
        state: dict[str, Any] | None = None,
        trace_id: Any | None = None,
        parent_id: str | None = None,
        **kwargs
) -> Iterator[ActivityAbout]:
    """
    Initializes a new span and logs its start at the TRACE level and duration at the INFO level by default.

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
        yield ActivityAbout(activity)
