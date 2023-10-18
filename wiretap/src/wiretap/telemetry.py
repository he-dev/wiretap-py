import asyncio
import contextlib
import functools
import inspect
from typing import Dict, Any, Optional, ContextManager, Callable

from .types import current_tracer
from .loggers import BasicLogger, TraceLogger


@contextlib.contextmanager
def telemetry_context(
        subject: str,
        activity: str
) -> ContextManager[TraceLogger]:  # noqa
    parent = current_tracer.get()
    logger = BasicLogger(subject, activity, parent.default if parent else None)
    tracer = TraceLogger(logger)
    token = current_tracer.set(tracer)
    try:
        yield tracer
    except Exception as e:  # noqa
        tracer.final.log_error(message="Unhandled exception has occurred.")
        raise
    finally:
        current_tracer.reset(token)


@contextlib.contextmanager
def begin_telemetry(
        subject: str,
        activity: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        attachment: Optional[Any] = None
) -> ContextManager[TraceLogger]:  # noqa
    with telemetry_context(subject, activity) as tracer:
        tracer.initial.log_begin(message, details, attachment)
        yield tracer
        tracer.final.log_end()


def telemetry(
        include_args: Optional[dict[str, str | Callable | None] | bool] = False,
        include_result: Optional[str | Callable | bool] = False,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        attachment: Optional[Any] = None
):
    """Provides telemetry for the decorated function."""

    details = details or {}

    def factory(decoratee):
        module = inspect.getmodule(decoratee)
        subject = module.__name__ if module else None
        activity = decoratee.__name__

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
                with telemetry_context(subject, activity) as logger:
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
                with telemetry_context(subject, activity) as logger:
                    logger.initial.log_begin(message=message, details=details | dict(args_native=args, args_format=include_args) or {}, attachment=attachment)
                    inject_logger(logger, decoratee_kwargs)
                    result = decoratee(*decoratee_args, **decoratee_kwargs)
                    logger.final.log_end(details=dict(result_native=result, result_format=include_result))
                    return result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

    return factory
