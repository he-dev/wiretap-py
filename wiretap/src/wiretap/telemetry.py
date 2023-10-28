import asyncio
import functools
import inspect
from pathlib import Path
from typing import Any, Callable, TypeVar, Generic

from .tracing import Activity, OnBegin, OnError


def telemetry(
        alias: str | None = None,
        include_args: dict[str, str | Callable | None] | bool | None = False,
        include_result: str | Callable | bool | None = False,
        auto_begin=True,
        on_begin: OnBegin | None = None,
        on_error: OnError | None = None
):
    """Provides telemetry for the decorated function."""

    on_begin = on_begin or (lambda _t: _t)
    on_error = on_error or (lambda _exc, _logger: None)

    def factory(decoratee):
        stack = inspect.stack()
        frame = stack[1]
        kwargs_with_activity = KwargsWithActivity(decoratee)

        if asyncio.iscoroutinefunction(decoratee):
            @functools.wraps(decoratee)
            async def decorator(*decoratee_args, **decoratee_kwargs):
                args = get_args(decoratee, *decoratee_args, **decoratee_kwargs)
                activity = Activity(
                    name=alias or decoratee.__name__,
                    file=Path(frame.filename).name,
                    line=frame.lineno,
                    auto_begin=auto_begin,
                    on_begin=lambda t: t.action(on_begin).with_details(args_native=args, args_format=include_args),
                    on_error=on_error
                )
                with activity:
                    result = await decoratee(*decoratee_args, **kwargs_with_activity(decoratee_kwargs, activity))
                    activity.final.trace_end().with_details(result_native=result, result_format=include_result).log()
                    return result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

        else:
            @functools.wraps(decoratee)
            def decorator(*decoratee_args, **decoratee_kwargs):
                args = get_args(decoratee, *decoratee_args, **decoratee_kwargs)
                activity = Activity(
                    name=alias or decoratee.__name__,
                    file=Path(frame.filename).name,
                    line=frame.lineno,
                    auto_begin=auto_begin,
                    on_begin=lambda t: t.action(on_begin).with_details(args_native=args, args_format=include_args),
                    on_error=on_error
                )
                with activity:
                    result = decoratee(*decoratee_args, **kwargs_with_activity(decoratee_kwargs, activity))
                    activity.final.trace_end().with_details(result_native=result, result_format=include_result).log()
                    return result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

    return factory


_Func = TypeVar("_Func", bound=Callable)


class KwargsWithActivity(Generic[_Func]):
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
