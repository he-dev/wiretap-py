import contextlib
import inspect
import logging
import sys
import uuid
from enum import Enum
from typing import Optional, Any, Iterator, Callable, Type, Tuple

from . import filters
from . import formatters
from . import json
from . import scopes
from . import tag
from .context import current_activity
from .scopes import ActivityScope, LoopScope

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
        tags: set[str | Enum] | None = None,
        **kwargs
) -> Iterator[ActivityScope]:
    """This function logs telemetry for an activity scope. It returns the activity scope that provides additional APIs."""
    tags = (tags or set())  # | {tag.AUTO}
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
        exc_cls, exc, exc_tb = sys.exc_info()
        if exc is not None:
            scope.log_error(tags={tag.UNHANDLED})
        raise
    finally:
        scope.log_end()
        current_activity.reset(token)


def log_error(
        message: str | None = None,
        snapshot: dict | None = None,
        tags: set[str | Enum] | None = None,
        exc_info: bool = True,
        **kwargs
) -> None:
    parent = current_activity.get()
    if parent:
        parent.value.log_error(message, snapshot, tags, exc_info=exc_info, **kwargs)


def log_resource(
        name: str,
        message: str | None = None,
        snapshot: dict[str, Any] | None = None,
        tags: set[str | Enum] | None = None,
        **kwargs
) -> Callable[[], None]:
    """This function logs telemetry for a resource. It returns a function that logs the end of its usage when called."""
    scope = log_activity(name, message, snapshot, tags, **kwargs)
    scope.__enter__()

    def dispose():
        scope.__exit__(None, None, None)

    return dispose


@contextlib.contextmanager
def log_loop(
        activity: ActivityScope,
        message: str | None = None,
        tags: set[str | Enum] | None = None,
        **kwargs,
) -> Iterator[LoopScope]:
    """This function initializes a new scope for loop telemetry."""
    scope = LoopScope()
    try:
        yield scope
    finally:
        activity.log_trace(
            name="loop",
            message=message,
            snapshot=scope.dump(),
            tags=tags,
            **kwargs
        )


def no_exc_info_if(exception_type: Type[BaseException] | Tuple[Type[BaseException], ...]) -> bool:
    exc_cls, exc, exc_tb = sys.exc_info()
    return not isinstance(exc, exception_type)


def to_tag(value: str | Enum) -> str:
    if isinstance(value, Enum):
        value = str(value)

    return value.replace("_", "-")
