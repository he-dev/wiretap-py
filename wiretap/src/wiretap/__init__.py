import contextlib
import inspect
import logging
import sys
import uuid
from typing import Optional, Any, Iterator, Callable, Type, Tuple

from . import filters
from . import formatters
from . import json
from . import scopes
from . import tag
from .context import current_activity
from .scopes import ActivityScope

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {activity_name} | {trace_name} | {activity_elapsed}s | {trace_message} | {trace_snapshot} | {trace_tags}"

DEFAULT_FILTERS: list[logging.Filter | Callable[[logging.LogRecord], bool]] = [
    filters.AddTimestampExtra(tz="utc"),
    filters.AddDefaultActivity(),
    filters.AddCurrentActivity(),
    filters.DumpException()
]


def dict_config(data: dict, default_filters: Optional[list[logging.Filter | Callable[[logging.LogRecord], bool]]] = None):
    import logging.config
    logging.config.dictConfig(data)
    for handler in logging.root.handlers:
        handler.filters = (default_filters or DEFAULT_FILTERS) + handler.filters


@contextlib.contextmanager
def log_activity(
        name: str | None = None,
        message: str | None = None,
        snapshot: dict[str, Any] | None = None,
        tags: set[str] | None = None,
        **kwargs
) -> Iterator[ActivityScope]:
    """This function logs telemetry for an activity scope. It returns the activity scope that provides additional APIs."""
    tags = (tags or set()) | {tag.AUTO}
    if name:
        tags.add(tag.VIRTUAL)

    from _reusable import Node
    stack = inspect.stack(2)
    frame = stack[2]
    scope = ActivityScope(name=name or frame.function, frame=frame, snapshot=snapshot, tags=tags, **kwargs)
    parent = current_activity.get()
    # The UUID needs to be created here,
    # because for some stupid pythonic reason creating a new Node isn't enough.
    token = current_activity.set(Node(value=scope, parent=parent, id=scope.id))
    try:
        scope.log_trace(name="begin", message=message, snapshot=snapshot, **kwargs)
        yield scope
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if exc_type is not None:
            scope.log_error(tags={tag.UNHANDLED})
        raise
    finally:
        scope.log_end()
        current_activity.reset(token)


def log_resource(
        name: str,
        message: str | None = None,
        snapshot: dict[str, Any] | None = None,
        tags: set[str] | None = None,
        **kwargs
) -> Callable[[], None]:
    """This function logs telemetry for a resource. It returns a function that logs the end of its usage when called."""
    scope = log_activity(name, message, snapshot, tags, **kwargs)
    scope.__enter__()

    def dispose():
        scope.__exit__(None, None, None)

    return dispose


def no_exc_info_if(exception_type: Type[BaseException] | Tuple[Type[BaseException], ...]) -> bool:
    exc_cls, exc, exc_tb = sys.exc_info()
    return not isinstance(exc, exception_type)
