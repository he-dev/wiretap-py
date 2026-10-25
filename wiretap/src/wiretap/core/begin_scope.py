import contextlib
from typing import Any, Iterator, Callable

from wiretap.util.activity import ActivityAbout, ActivityScope


@contextlib.contextmanager
def begin_scope(
        about: str,
        state: dict[str, Any] | None = None,
        trace_id: Any | None = None,
        **kwargs
) -> Iterator[ActivityAbout]:
    """
    Initializes a new span and logs its start at the TRACE level and duration at the INFO level by default.

    Args:
        about: The name of the span. If None, the name will be derived from the calling frame. Usually the function name.
        state: A dictionary of extra data to log that is attached to each trace.
        trace_id: The trace ID to use for the span. If None, a random ID will be generated.
        kwargs: Additional keyword arguments to be passed to each trace.

    Returns:
        The newly created span.
    """

    # stack = inspect.stack(2)
    # frame = stack[2]

    state = (state or {}) | kwargs
    parent = ActivityScope.get_current()
    with ActivityScope(about, state, trace_id, parent).push() as scope:
        try:
            yield ActivityAbout(scope)
        except Exception:
            raise
        finally:
            pass
