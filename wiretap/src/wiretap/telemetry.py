import asyncio
import contextlib
import functools
import inspect
from pathlib import Path
from typing import Dict, Any, Optional, ContextManager, Callable, Protocol

from .loggers import BasicLogger, TraceLogger
from .session import current_logger
from .types import Node, Source


class LogAbortWhen:
    def __init__(self, *error_types: type[Exception]):
        self.error_types = error_types

    def __call__(self, exc: Exception, logger: TraceLogger) -> bool:
        if any((isinstance(exc, t) for t in self.error_types)):
            logger.final.log_abort(message="Unable to complete.")
            return True
        return False


class OnError(Protocol):
    def __call__(self, exc: Exception, logger: TraceLogger) -> bool: ...


@contextlib.contextmanager
def telemetry_context(
        activity: str,
        source: Source,
        on_error: Optional[OnError] = None,
) -> ContextManager[TraceLogger]:  # noqa
    parent = current_logger.get()
    logger = BasicLogger(activity)
    tracer = TraceLogger(logger)
    tracer.initial.source.append(source)
    token = current_logger.set(Node(logger, parent))
    try:
        yield tracer
    except Exception as e:  # noqa
        if not on_error or not on_error(e, tracer):
            tracer.final.log_error(message="Unhandled exception has occurred.")
        raise
    finally:
        current_logger.reset(token)


@contextlib.contextmanager
def begin_telemetry(
        activity: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        attachment: Optional[Any] = None
) -> ContextManager[TraceLogger]:  # noqa
    stack = inspect.stack()
    frame = stack[2]
    source = Source(file=Path(frame.filename).name, line=frame.lineno)
    with telemetry_context(activity, source) as tracer:
        tracer.initial.log_begin(message, details, attachment)
        yield tracer
        tracer.final.log_end()


def telemetry(
        activity_alias: Optional[str] = None,
        include_args: Optional[dict[str, str | Callable | None] | bool] = False,
        include_result: Optional[str | Callable | bool] = False,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        attachment: Optional[Any] = None,
        auto_begin=True,
        on_error: Optional[OnError] = None
):
    """Provides telemetry for the decorated function."""

    details = details or {}

    def factory(decoratee):
        stack = inspect.stack()
        frame = stack[1]
        source = Source(file=Path(frame.filename).name, line=frame.lineno)
        # module = inspect.getmodule(decoratee)
        # subject = module.__name__ if module else None
        # subject = "s"  # f"{Path(frame.filename).name}: #{frame.lineno}"
        activity = activity_alias or decoratee.__name__

        def inject_logger(logger: TraceLogger, d: Dict):
            """Injects Logger if required."""
            for n, t in inspect.getfullargspec(decoratee).annotations.items():
                if t is BasicLogger:
                    d[n] = logger.default
                if t is TraceLogger:
                    d[n] = logger

        def get_args(*decoratee_args, **decoratee_kwargs) -> dict[str, Any]:
            # Zip arg names and their indexes up to the number of args of the decoratee_args.
            arg_pairs = zip(inspect.getfullargspec(decoratee).args, range(len(decoratee_args)))
            # Turn arg_pairs into a dictionary and combine it with decoratee_kwargs.
            return {t[0]: decoratee_args[t[1]] for t in arg_pairs} | decoratee_kwargs
            # No need to filter args as the logger is injected later.
            # return {k: v for k, v in result.items() if not isinstance(v, Logger)}

        if asyncio.iscoroutinefunction(decoratee):
            @functools.wraps(decoratee)
            async def decorator(*decoratee_args, **decoratee_kwargs):
                args = get_args(*decoratee_args, **decoratee_kwargs)
                with telemetry_context(activity, source, on_error) as logger:
                    if auto_begin:
                        logger.initial.log_begin(message=message, details=details | dict(args_native=args, args_format=include_args) or {}, attachment=attachment)
                    inject_logger(logger, decoratee_kwargs)
                    result = await decoratee(*decoratee_args, **decoratee_kwargs)
                    logger.final.log_end(details=dict(result_native=result, result_format=include_result))
                    return result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

        else:
            @functools.wraps(decoratee)
            def decorator(*decoratee_args, **decoratee_kwargs):
                args = get_args(*decoratee_args, **decoratee_kwargs)
                with telemetry_context(activity, source, on_error) as logger:
                    if auto_begin:
                        logger.initial.log_begin(message=message, details=details | dict(args_native=args, args_format=include_args) or {}, attachment=attachment)
                    inject_logger(logger, decoratee_kwargs)
                    result = decoratee(*decoratee_args, **decoratee_kwargs)
                    logger.final.log_end(details=dict(result_native=result, result_format=include_result))
                    return result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

    return factory
