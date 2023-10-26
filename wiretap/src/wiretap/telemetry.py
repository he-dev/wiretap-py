import asyncio
import contextlib
import dataclasses
import functools
import inspect
from pathlib import Path
from typing import Any, Optional, Callable, Protocol, Iterator, TypeVar, Generic

from .loggers import BasicLogger, TraceLogger, InitialTraceMissing
from .session import current_logger
from .types import Activity
from .parts import Node

OnError = Callable[[BaseException, TraceLogger], None]


@dataclasses.dataclass(frozen=True, slots=True)
class LogAbortWhen:
    exceptions: type[BaseException] | tuple[type[BaseException], ...]

    def __call__(self, exc: BaseException, logger: TraceLogger) -> None:
        if isinstance(exc, self.exceptions):
            logger.final.log_abort(message=f"Unable to complete due to <{type(exc).__name__}>: {str(exc) or '<N/A>'}")


@contextlib.contextmanager
def telemetry_context(
        activity: Activity,
        on_error: OnError = lambda _exc, _logger: None
) -> Iterator[TraceLogger]:  # | ContextManager[TraceLogger]:  # noqa
    parent = current_logger.get()
    logger = BasicLogger(activity)
    tracer = TraceLogger(logger)
    token = current_logger.set(Node(logger, parent))
    try:
        yield tracer
    except InitialTraceMissing:
        # Do nothing when this error occurs, otherwise the same exception will raise for the default handler.
        raise
    except Exception as e:  # noqa
        on_error(e, tracer)
        tracer.final.log_error(message=f"Unhandled <{type(e).__name__}> has occurred: <{str(e) or 'N/A'}>")
        raise
    finally:
        current_logger.reset(token)


@contextlib.contextmanager
def begin_telemetry(
        activity: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        attachment: Optional[Any] = None
) -> Iterator[TraceLogger]:  # | ContextManager[TraceLogger]:  # noqa
    stack = inspect.stack()
    frame = stack[2]
    with telemetry_context(Activity(name=activity, file=Path(frame.filename).name, line=frame.lineno)) as tracer:
        tracer.initial.log_begin(message, details, attachment)
        yield tracer
        tracer.final.log_end()


def telemetry(
        alias: Optional[str] = None,
        include_args: Optional[dict[str, str | Callable | None] | bool] = False,
        include_result: Optional[str | Callable | bool] = False,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        attachment: Optional[Any] = None,
        on_error: OnError = lambda _exc, _logger: None,
        auto_begin=True
):
    """Provides telemetry for the decorated function."""

    details = details or {}

    def factory(decoratee):
        stack = inspect.stack()
        frame = stack[1]
        activity = Activity(
            name=alias or decoratee.__name__,
            file=Path(frame.filename).name,
            line=frame.lineno
        )
        kwargs_with_logger = KwargsWithLogger(decoratee)

        if asyncio.iscoroutinefunction(decoratee):
            @functools.wraps(decoratee)
            async def decorator(*decoratee_args, **decoratee_kwargs):
                args = get_args(decoratee, *decoratee_args, **decoratee_kwargs)
                logger: TraceLogger
                with telemetry_context(activity, on_error) as logger:
                    if auto_begin:
                        logger.initial.log_begin(message=message, details=details | dict(args_native=args, args_format=include_args) or {}, attachment=attachment)
                    inject_logger(decoratee, decoratee_kwargs, logger)
                    result = await decoratee(*decoratee_args, **decoratee_kwargs)
                    logger.final.log_end(details=dict(result_native=result, result_format=include_result))
                    return result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

        else:
            @functools.wraps(decoratee)
            def decorator(*decoratee_args, **decoratee_kwargs):
                args = get_args(decoratee, *decoratee_args, **decoratee_kwargs)
                logger: TraceLogger  # PyCharm doesn't understand context managers.
                with telemetry_context(activity, on_error) as logger:
                    if auto_begin:
                        logger.initial.log_begin(message=message, details=details | dict(args_native=args, args_format=include_args) or {}, attachment=attachment)
                    result = decoratee(*decoratee_args, **kwargs_with_logger(decoratee_kwargs, logger))
                    logger.final.log_end(details=dict(result_native=result, result_format=include_result))
                    return result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

    return factory


_Func = TypeVar("_Func", bound=Callable)


class KwargsWithLogger(Generic[_Func]):
    def __init__(self, func: _Func):
        # Find the name of the logger-argument if any...
        self.name = next((n for n, t in inspect.getfullargspec(func).annotations.items() if t is TraceLogger), "")

    def __call__(self, kwargs: dict[str, Any], logger: TraceLogger) -> dict[str, Any]:
        # If name exists, then the key definitely is there so no need to check twice.
        if self.name:
            kwargs[self.name] = logger
        return kwargs


def inject_logger(func: object, kwargs: dict[str, Any], logger: TraceLogger) -> None:
    for n, t in inspect.getfullargspec(func).annotations.items():
        if t is BasicLogger:
            kwargs[n] = logger.default
        if t is TraceLogger:
            kwargs[n] = logger


def get_args(decoratee: object, *args, **kwargs) -> dict[str, Any]:
    # Zip arg names and their indexes up to the number of args of the decoratee_args.
    arg_pairs = zip(inspect.getfullargspec(decoratee).args, range(len(args)))
    # Turn arg_pairs into a dictionary and combine it with decoratee_kwargs.
    return {t[0]: args[t[1]] for t in arg_pairs} | kwargs
