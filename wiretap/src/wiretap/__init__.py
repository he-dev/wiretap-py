import contextlib
import inspect
import sys
from typing import Any, Iterator, Type, Tuple, ContextManager

from .data import TraceTag, LogTrace
from .scopes import LoggerScope, current_scope
from .scopes.iteration_scope import IterationScope


def dict_config(config: dict):
    import logging.config
    logging.config.dictConfig(config)


@contextlib.contextmanager
def _log_begin(
        name: str | None,
        message: str | None,
        tags: set[Any] | None,
        log_trace: LogTrace,
        **kwargs
) -> Iterator[LoggerScope]:
    """This function logs telemetry for an activity scope. It returns the activity scope that provides additional APIs."""

    stack = inspect.stack(2)
    frame = stack[2]

    with LoggerScope.push(kwargs.pop("id", None), name, tags, frame) as scope:
        try:
            log_trace(
                self=scope,
                name="begin",
                message=message,
                state={
                    "func": scope.frame.function,
                    "file": scope.frame.filename,
                    "line": scope.frame.lineno
                },
                tags={TraceTag.AUTO}
            )
            yield scope
        except Exception:
            exc_cls, exc, exc_tb = sys.exc_info()
            if exc is not None:
                scope.log_exception(tags={TraceTag.AUTO})
            raise
        finally:
            log_trace(self=scope, name="end",tags={TraceTag.AUTO}, in_progress=False)


def info_scope(
        name: str | None = None,
        message: str | None = None,
        tags: set[Any] | None = None,
        **kwargs
) -> ContextManager[LoggerScope]:
    return _log_begin(name, message, tags, LoggerScope.log_info, **kwargs)


def debug_scope(
        name: str | None = None,
        message: str | None = None,
        tags: set[Any] | None = None,
        **kwargs
) -> ContextManager[LoggerScope]:
    return _log_begin(name, message, tags, LoggerScope.log_debug, **kwargs)


@contextlib.contextmanager
def info_loop(
        name: str | None = "loop",
        message: str | None = None,
        tags: set[Any] | None = None,
        **kwargs
) -> Iterator[IterationScope]:
    loop = IterationScope()
    try:
        yield loop
    finally:
        LoggerScope.peek().log_info(
            name=name,
            message=message,
            state=loop.dump(),
            tags=(tags or set()) | {TraceTag.LOOP, TraceTag.AUTO},
            **kwargs
        )


@contextlib.contextmanager
def debug_loop(
        name: str | None = "loop",
        message: str | None = None,
        tags: set[Any] | None = None,
        **kwargs
) -> Iterator[IterationScope]:
    loop = IterationScope()
    try:
        yield loop
    finally:
        LoggerScope.peek().log_debug(
            name=name,
            message=message,
            state=loop.dump(),
            tags=(tags or set()) | {TraceTag.LOOP},
            **kwargs
        )


@contextlib.contextmanager
def none_block(
        name: str | None = None,
        tags: set[Any] | None = None
) -> Iterator[LoggerScope]:
    stack = inspect.stack(2)
    frame = stack[2]
    with LoggerScope.push(None, name, tags, frame) as scope:
        yield scope


def no_exc_info_if(exception_type: Type[BaseException] | Tuple[Type[BaseException], ...]) -> bool:
    exc_cls, exc, exc_tb = sys.exc_info()
    return not isinstance(exc, exception_type)


def to_tag(value: Any) -> str:
    return str(value).replace("_", "-")
