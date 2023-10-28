import asyncio
import contextlib
import dataclasses
import functools
import inspect
from pathlib import Path
from typing import Any, Optional, Callable, Iterator, TypeVar, Generic

from .tracing import Activity, ActivityStartMissing, ActivityAlreadyStarted, PreviousTraceNotLogged, ActivityStartLogged
from .session import current_activity
from .parts import Node

OnError = Callable[[BaseException, Activity], None]


@dataclasses.dataclass(frozen=True, slots=True)
class LogAbortWhen:
    exceptions: type[BaseException] | tuple[type[BaseException], ...]

    def __call__(self, exc: BaseException, logger: Activity) -> None:
        if isinstance(exc, self.exceptions):
            logger.final.trace_abort(f"Unable to complete due to <{type(exc).__name__}>: {str(exc) or '<N/A>'}").log()


@contextlib.contextmanager
def telemetry_context(
        activity: Activity,
        on_error: OnError = lambda _exc, _logger: None
) -> Iterator[Activity]:  # | ContextManager[TraceLogger]:  # noqa
    parent = current_activity.get()
    token = current_activity.set(Node(activity, parent))
    try:
        yield activity
    except (ActivityStartMissing, ActivityAlreadyStarted, PreviousTraceNotLogged):
        # Do nothing when this error occurs, otherwise the same exception will raise for the default handler.
        raise
    except Exception as e:  # noqa
        on_error(e, activity)
        activity.final.trace_error(f"Unhandled <{type(e).__name__}> has occurred: <{str(e) or 'N/A'}>").log()
        raise
    finally:
        current_activity.reset(token)


@contextlib.contextmanager
def begin_telemetry(
        activity: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        attachment: Optional[Any] = None
) -> Iterator[Activity]:  # | ContextManager[TraceLogger]:  # noqa
    stack = inspect.stack()
    frame = stack[2]
    logger: Activity
    with telemetry_context(Activity(name=activity, file=Path(frame.filename).name, line=frame.lineno)) as logger:
        logger.start.trace_begin().with_message(message).with_details(**(details or {})).with_attachment(attachment).log()
        yield logger
        logger.final.trace_end().with_details().log()


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
                logger: Activity
                with telemetry_context(activity, on_error) as logger:
                    if auto_begin:
                        logger.start.trace_begin().with_message(message).with_details(**(details or {})).with_details(args_native=args, args_format=include_args).with_attachment(attachment).log()
                    result = await decoratee(*decoratee_args, **kwargs_with_logger(decoratee_kwargs, logger))
                    logger.final.trace_end().with_details(result_native=result, result_format=include_result).log()
                    return result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

        else:
            @functools.wraps(decoratee)
            def decorator(*decoratee_args, **decoratee_kwargs):
                args = get_args(decoratee, *decoratee_args, **decoratee_kwargs)
                logger: Activity  # PyCharm doesn't understand context managers.
                with telemetry_context(activity, on_error) as logger:
                    if auto_begin:
                        logger.start.trace_begin().with_message(message).with_details(**(details or {})).with_details(args_native=args, args_format=include_args).with_attachment(attachment).log()
                    result = decoratee(*decoratee_args, **kwargs_with_logger(decoratee_kwargs, logger))
                    logger.final.trace_end().with_details(result_native=result, result_format=include_result).log()
                    return result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

    return factory


_Func = TypeVar("_Func", bound=Callable)


class KwargsWithLogger(Generic[_Func]):
    def __init__(self, func: _Func):
        # Find the name of the logger-argument if any...
        self.name = next((n for n, t in inspect.getfullargspec(func).annotations.items() if t is Activity), "")

    def __call__(self, kwargs: dict[str, Any], logger: Activity) -> dict[str, Any]:
        # If name exists, then the key definitely is there so no need to check twice.
        if self.name:
            kwargs[self.name] = logger
        return kwargs


def get_args(decoratee: object, *args, **kwargs) -> dict[str, Any]:
    # Zip arg names and their indexes up to the number of args of the decoratee_args.
    arg_pairs = zip(inspect.getfullargspec(decoratee).args, range(len(args)))
    # Turn arg_pairs into a dictionary and combine it with decoratee_kwargs.
    return {t[0]: args[t[1]] for t in arg_pairs} | kwargs
