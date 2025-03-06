import contextlib
import inspect
import logging
import sys
from typing import Any, Iterator, Type, Tuple, ContextManager, cast, ClassVar, Callable, Protocol

from .data import TraceTag
from .scopes.telemetry_scope import TelemetryScope
from .scopes.iteration_scope import IterationScope
from .telemetry import Telemetry


def dict_config(config: dict):
    import logging.config
    logging.config.dictConfig(config)


@contextlib.contextmanager
def _log_begin(
        name: str | None,
        message: str | None,
        tags: set[Any] | None,
        level: int,
        **kwargs
) -> Iterator[Telemetry]:
    """This function logs telemetry for an activity scope. It returns the activity scope that provides additional APIs."""

    stack = inspect.stack(2)
    frame = stack[2]

    custom_id = kwargs.pop("id", None)  # The caller can override the default id.
    with TelemetryScope.push(custom_id, name, tags, frame) as scope:
        telemetry = Telemetry(scope)
        try:
            telemetry.log_trace(
                name="begin",
                message=message,
                state={
                    "func": scope.frame.function,
                    "file": scope.frame.filename,
                    "line": scope.frame.lineno
                } if scope.logger.isEnabledFor(logging.DEBUG) else {},
                tags={TraceTag.AUTO},
                level=level,
                is_final=False
            )
            yield telemetry
        except Exception:
            # exc_cls, exc, exc_tb = sys.exc_info()
            # if exc is not None:
            telemetry.log_exception(tags={TraceTag.AUTO})
            raise
        finally:
            telemetry.log_trace(
                name="end",
                tags={TraceTag.AUTO},
                level=level,
                is_final=True
            )


def info_scope(
        name: str | None = None,
        message: str | None = None,
        tags: set[Any] | None = None,
        **kwargs
) -> ContextManager[Telemetry]:
    return _log_begin(name, message, tags, logging.INFO, **kwargs)


def debug_scope(
        name: str | None = None,
        message: str | None = None,
        tags: set[Any] | None = None,
        **kwargs
) -> ContextManager[Telemetry]:
    return _log_begin(name, message, tags, logging.DEBUG, **kwargs)


@contextlib.contextmanager
def info_loop(
        name: str = "loop",
        message: str | None = None,
        tags: set[Any] | None = None,
        **kwargs
) -> Iterator[IterationScope]:
    loop = IterationScope()
    try:
        yield loop
    finally:
        Telemetry().log_info(
            name=name,
            message=message,
            state=loop.dump(),
            tags=(tags or set()) | {TraceTag.LOOP, TraceTag.AUTO},
            **kwargs
        )


@contextlib.contextmanager
def debug_loop(
        name: str = "loop",
        message: str | None = None,
        tags: set[Any] | None = None,
        **kwargs
) -> Iterator[IterationScope]:
    loop = IterationScope()
    try:
        yield loop
    finally:
        Telemetry().log_debug(
            name=name,
            message=message,
            state=loop.dump(),
            tags=(tags or set()) | {TraceTag.LOOP},
            **kwargs
        )


@contextlib.contextmanager
def none_block(
        name: str = "none",
        tags: set[Any] | None = None
) -> Iterator[Telemetry]:
    stack = inspect.stack(2)
    frame = stack[2]
    with TelemetryScope.push(None, name, tags, frame) as scope:
        yield Telemetry(scope)


def no_exc_info_if(exception_type: Type[BaseException] | Tuple[Type[BaseException], ...]) -> bool:
    exc_cls, exc, exc_tb = sys.exc_info()
    return not isinstance(exc, exception_type)


def to_tag(value: Any) -> str:
    return str(value).replace("_", "-")
