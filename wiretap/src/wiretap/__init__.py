import contextlib
import inspect
import sys
from typing import Any, Iterator, Type, Tuple, ContextManager

from . import formatters
from . import json
from . import tag
from .context import current_procedure
from .contexts import ProcedureContext
from .data import Correlation


def dict_config(config: dict):
    import logging.config
    logging.config.dictConfig(config)


@contextlib.contextmanager
def log_procedure(
        enclosing_trace_names: Tuple[str, str, str] = ("begin", "end", "error"),
        name: str | None = None,
        message: str | None = None,
        data: dict[str, Any] | None = None,
        tags: set[Any] | None = None,
        correlation_id: Any | None = None,
        **kwargs
) -> Iterator[ProcedureContext]:
    """This function logs telemetry for an activity scope. It returns the activity scope that provides additional APIs."""
    from _reusable import Node
    stack = inspect.stack(2)
    frame = stack[2]
    parent = current_procedure.get()

    correlation: Correlation | None = None
    if parent:
        correlation = parent.value.correlation

    if correlation_id:
        correlation = Correlation(id=correlation_id, type="custom")

    activity = ProcedureContext(
        frame=frame,
        parent=parent.value if parent else None,
        name=name,
        data=data,
        tags=tags,
        correlation=correlation,
        **kwargs
    )
    token = current_procedure.set(Node(value=activity, parent=parent, id=activity.id))
    try:
        activity.log_trace(name=enclosing_trace_names[0], message=message)
        yield activity
    except Exception:
        exc_cls, exc, exc_tb = sys.exc_info()
        if exc is not None:
            activity.log_last(name=enclosing_trace_names[2], tags={tag.UNHANDLED}, exc_info=True)
        raise
    finally:
        activity.log_last(name=enclosing_trace_names[1])
        current_procedure.reset(token)


def log_begin(
        name: str | None = None,
        message: str | None = None,
        body: dict[str, Any] | None = None,
        tags: set[Any] | None = None,
        correlation_id: Any | None = None,
        **kwargs
) -> ContextManager[ProcedureContext]:
    return log_procedure(
        enclosing_trace_names=("begin", "end", "error"),
        name=name,
        message=message,
        data=body,
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
) -> ContextManager[ProcedureContext]:
    return log_procedure(
        enclosing_trace_names=("connect", "disconnect", "error"),
        name=name,
        message=message,
        data=body,
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
) -> ContextManager[ProcedureContext]:
    return log_procedure(
        enclosing_trace_names=("open", "close", "error"),
        name=name,
        message=message,
        data=body,
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
) -> ContextManager[ProcedureContext]:
    return log_procedure(
        enclosing_trace_names=("begin", "commit", "rollback"),
        name=name,
        message=message,
        data=body,
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


def to_tag(value: Any) -> str:
    return str(value).replace("_", "-")
