import contextlib
import inspect
import sys
from enum import Enum
from typing import Any, Iterator, Type, Tuple, ContextManager

from . import formatters
from . import json
from . import tag
from .context import current_activity
from .contexts import ActivityContext
from .data import Correlation


def dict_config(config: dict):
    import logging.config
    logging.config.dictConfig(config)


@contextlib.contextmanager
def log_activity(
        enclosing_trace_codes: Tuple[str, str, str] = ("begin", "end", "error"),
        name: str | None = None,
        message: str | None = None,
        body: dict[str, Any] | None = None,
        tags: set[Any] | None = None,
        correlation_id: Any | None = None,
        **kwargs
) -> Iterator[ActivityContext]:
    """This function logs telemetry for an activity scope. It returns the activity scope that provides additional APIs."""
    tags = (tags or set())
    from _reusable import Node
    stack = inspect.stack(2)
    frame = stack[2]
    parent = current_activity.get()

    correlation: Correlation | None = None
    if parent:
        correlation = parent.value.correlation

    if correlation_id:
        correlation = Correlation(id=correlation_id, type="custom")

    activity = ActivityContext(
        parent=parent.value if parent else None,
        func=frame.function,
        name=name,
        frame=frame,
        body=body,
        tags=tags,
        correlation=correlation,
        **kwargs
    )
    # The UUID needs to be created here,
    # because for some stupid pythonic reason creating a new Node isn't enough.
    token = current_activity.set(Node(value=activity, parent=parent, id=activity.id))
    try:
        activity.log_trace(code=enclosing_trace_codes[0], message=message, body={})
        yield activity
    except Exception:
        exc_cls, exc, exc_tb = sys.exc_info()
        if exc is not None:
            # activity.log_error(tags={tag.UNHANDLED})
            activity.log_last(code=enclosing_trace_codes[2], tags={tag.UNHANDLED}, exc_info=True)
        raise
    finally:
        activity.log_trace(code=enclosing_trace_codes[1], in_progress=False)
        current_activity.reset(token)


def log_begin(
        name: str | None = None,
        message: str | None = None,
        body: dict[str, Any] | None = None,
        tags: set[Any] | None = None,
        correlation_id: Any | None = None,
        **kwargs
) -> ContextManager[ActivityContext]:
    return log_activity(
        enclosing_trace_codes=("begin", "end", "error"),
        name=name,
        message=message,
        body=body,
        tags=tags,
        correlation_id=correlation_id,
        **kwargs
    )


def log_connect(
        name: str | None = None,
        message: str | None = None,
        body: dict[str, Any] | None = None,
        tags: set[Any] | None = None,
        correlation_id: Any | None = None,
        **kwargs
) -> ContextManager[ActivityContext]:
    return log_activity(
        enclosing_trace_codes=("connect", "disconnect", "error"),
        name=name,
        message=message,
        body=body,
        tags=tags,
        correlation_id=correlation_id,
        **kwargs
    )


def log_open(
        name: str | None = None,
        message: str | None = None,
        body: dict[str, Any] | None = None,
        tags: set[Any] | None = None,
        correlation_id: Any | None = None,
        **kwargs
) -> ContextManager[ActivityContext]:
    return log_activity(
        enclosing_trace_codes=("open", "close", "error"),
        name=name,
        message=message,
        body=body,
        tags=tags,
        correlation_id=correlation_id,
        **kwargs
    )


def log_transaction(
        name: str | None = None,
        message: str | None = None,
        body: dict[str, Any] | None = None,
        tags: set[Any] | None = None,
        correlation_id: Any | None = None,
        **kwargs
) -> ContextManager[ActivityContext]:
    return log_activity(
        enclosing_trace_codes=("begin", "commit", "rollback"),
        name=name,
        message=message,
        body=body,
        tags=tags,
        correlation_id=correlation_id,
        **kwargs
    )


# def log_resource(
#         name: str,
#         message: str | None = None,
#         note: dict[str, Any] | None = None,
#         tags: set[str] | None = None,
#         **kwargs
# ) -> Callable[[], None]:
#     """This function logs telemetry for a resource. It returns a function that logs the end of its usage when called."""
#     scope = log_activity(name, message, note, tags, **kwargs)
#     scope.__enter__()
#
#     def dispose():
#         scope.__exit__(None, None, None)
#
#     return dispose


def no_exc_info_if(exception_type: Type[BaseException] | Tuple[Type[BaseException], ...]) -> bool:
    exc_cls, exc, exc_tb = sys.exc_info()
    return not isinstance(exc, exception_type)


def to_tag(value: str | Enum) -> str:
    if isinstance(value, Enum):
        value = str(value)

    return value.replace("_", "-")
