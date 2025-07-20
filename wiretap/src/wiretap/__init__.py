import contextlib
import inspect
import logging
import sys
from typing import Any, Iterator, Callable, Optional

from .scopes.activity_scope import ActivityScope
from .stats import LoopStats
from .stats.basic import BasicStats
from .stats.welford import WelfordStats


def dict_config(config: dict):
    import logging.config
    logging.addLevelName(5, "TRACE")
    logging.config.dictConfig(config)


@contextlib.contextmanager
def begin_scope(
        name: str | None = None,
        state: dict[str, Any] | None = None,
        trace_id: Any | None = None,
        span_id: Any | None = None,
        **kwargs
) -> Iterator[ActivityScope]:
    """
    Initializes a new telemetry scope and logs its start, exception, and end.
    This can be disabled by setting the 'lite' parameter to True.

    :param name: The name of the scope. If None, the name will be derived from the calling frame. Usually the function name.
    :param state: A dictionary of extra data to log that is attached to each trace.
    :param kwargs: Additional keyword arguments to be passed to each trace.

    """

    stack = inspect.stack(2)
    frame = stack[2]

    with ActivityScope.push(name, trace_id=trace_id, span_id=span_id, state=state, frame=frame, **kwargs) as activity:
        yield activity


@contextlib.contextmanager
def log_scope():
    activity = ActivityScope.peek()
    try:
        activity.log_event(message=f"{activity} starts.", event="start")
        yield
        activity.log_event(message=f"{activity} complete.", event="success")
    except Exception:
        activity.log_event(message=f"{activity} failed.", event="failure", level=logging.ERROR)
        raise


def log_core(message: str, state: Optional[dict] = None, **kwargs) -> ActivityScope:
    return ActivityScope.peek().log_event(message=message, level=logging.INFO, state=state, frame_offset=2, role="core", **kwargs)


def log_util(message: str, state: Optional[dict] = None, **kwargs) -> ActivityScope:
    return ActivityScope.peek().log_event(message=message, level=logging.DEBUG, state=state, frame_offset=2, role="util", **kwargs)


def log_meta(message: str, state: Optional[dict] = None, **kwargs) -> ActivityScope:
    return ActivityScope.peek().log_event(message=message, level=5, state=state, frame_offset=2, role="meta", **kwargs)


def log_warning(message: str, state: Optional[dict] = None, **kwargs) -> ActivityScope:
    return ActivityScope.peek().log_event(message=message, level=logging.WARNING, state=state, frame_offset=2, **kwargs)


def log_error(message: str, state: Optional[dict] = None, **kwargs) -> ActivityScope:
    return ActivityScope.peek().log_event(message=message, level=logging.ERROR, state=state, frame_offset=2, **kwargs)


def add_next(stats_cls: type[LoopStats] = BasicStats) -> None:
    if scope := ActivityScope.peek():
        if parent := scope.parent:
            loop = parent.local.get("loop", None)
            if not loop:
                loop = stats_cls()
                scope.parent.local["loop"] = loop
            loop.collect(scope.elapsed.current, smooth=sys.exc_info()[0] is None)
        else:
            raise Exception("Cannot add next trace outside of a loop scope.")
    else:
        raise Exception("Cannot add next trace outside of a telemetry scope.")


def log_loop(message: str, state: Optional[dict] = None, **kwargs):
    if scope := ActivityScope.peek():
        if loop := scope.local.pop("loop", None):
            return ActivityScope.peek().log_event(message=message, level=logging.INFO, state=state, frame_offset=2, loop=loop, role="core", **kwargs)
        else:
            raise Exception("Cannot add next trace outside of a loop scope.")
    else:
        raise Exception("Cannot log_loop outside of a telemetry scope.")
