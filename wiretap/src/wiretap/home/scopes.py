import contextlib
import inspect
import logging
from typing import Any, Iterator

from wiretap.core.activity_scope import ActivityScope


@contextlib.contextmanager
def begin_scope(
        name: str | None = None,
        state: dict[str, Any] | None = None,
        trace_id: Any | None = None,
        parent_id: Any | None = None,
        **kwargs
) -> Iterator[ActivityScope]:
    """
    Initializes a new telemetry scope and logs its start, exception, and end.
    This can be disabled by setting the 'lite' parameter to True.

    :param name: The name of the scope. If None, the name will be derived from the calling frame. Usually the function name.
    :param state: A dictionary of extra data to log that is attached to each trace.
    :param kwargs: Additional keyword arguments to be passed to each trace.

    """

    stack = inspect.stack(2)
    frame = stack[2]

    with ActivityScope.push(name, trace_id=trace_id, parent_id=parent_id, state=state, frame=frame, **kwargs) as scope:
        yield scope


@contextlib.contextmanager
def log_scope():
    try:
        ActivityScope.log_event(message="Activity starts.", event="start")
        yield
        ActivityScope.log_event(message="Activity complete.", event="success")
    except Exception:
        ActivityScope.log_event(message="Activity failed.", event="failure", level=logging.ERROR)
        raise
