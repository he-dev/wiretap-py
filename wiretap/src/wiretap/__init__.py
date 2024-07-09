import contextlib
import inspect
import sys
from typing import Any, Iterator, Type, Tuple, ContextManager

from . import tag
from .context import current_procedure
from .contexts import ProcedureContext


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
        **kwargs
) -> Iterator[ProcedureContext]:
    """This function logs telemetry for an activity scope. It returns the activity scope that provides additional APIs."""
    from _reusable import Node
    stack = inspect.stack(2)
    frame = stack[2]
    parent = current_procedure.get()

    procedure = ProcedureContext(
        func=frame.function,
        file=frame.filename,
        line=frame.lineno,
        parent=parent.value if parent else None,
        name=name or frame.function,
        data=data,
        tags=tags,
        **kwargs
    )
    token = current_procedure.set(Node(value=procedure, parent=parent, id=procedure.id))
    try:
        procedure.log_trace(name=enclosing_trace_names[0], message=message)
        yield procedure
    except Exception:
        exc_cls, exc, exc_tb = sys.exc_info()
        if exc is not None:
            procedure.log_last(name=enclosing_trace_names[2], tags={tag.UNHANDLED}, exc_info=True)
        raise
    finally:
        procedure.log_last(name=enclosing_trace_names[1])
        current_procedure.reset(token)


def log_begin(
        name: str | None = None,
        message: str | None = None,
        data: dict[str, Any] | None = None,
        tags: set[Any] | None = None,
        **kwargs
) -> ContextManager[ProcedureContext]:
    return log_procedure(
        enclosing_trace_names=("begin", "end", "error"),
        name=name,
        message=message,
        data=data,
        tags=tags,
        **kwargs
    )


def log_connect(
        name: str | None = None,
        message: str | None = None,
        data: dict[str, Any] | None = None,
        tags: set[Any] | None = None,
        **kwargs
) -> ContextManager[ProcedureContext]:
    return log_procedure(
        enclosing_trace_names=("connect", "disconnect", "error"),
        name=name,
        message=message,
        data=data,
        tags=tags,
        **kwargs
    )


def log_open(
        name: str | None = None,
        message: str | None = None,
        data: dict[str, Any] | None = None,
        tags: set[Any] | None = None,
        **kwargs
) -> ContextManager[ProcedureContext]:
    return log_procedure(
        enclosing_trace_names=("open", "close", "error"),
        name=name,
        message=message,
        data=data,
        tags=tags,
        **kwargs
    )


def log_transaction(
        name: str | None = None,
        message: str | None = None,
        data: dict[str, Any] | None = None,
        tags: set[Any] | None = None,
        **kwargs
) -> ContextManager[ProcedureContext]:
    return log_procedure(
        enclosing_trace_names=("begin", "commit", "rollback"),
        name=name,
        message=message,
        data=data,
        tags=tags,
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
