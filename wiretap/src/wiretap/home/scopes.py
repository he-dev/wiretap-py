import contextlib
import inspect
import logging
from typing import Any, Iterator, Literal

from wiretap.core import TRACE_LEVEL, NoActivityInScopeError, SpanStatus
from wiretap.core.span import Span


@contextlib.contextmanager
def begin_scope(
        name: str | None = None,
        state: dict[str, Any] | None = None,
        trace_id: Any | None = None,
        parent_id: Any | None = None,
        **kwargs
) -> Iterator[Span]:
    """
    Initializes a new telemetry scope and logs its start, exception, and end.
    This can be disabled by setting the 'lite' parameter to True.

    :param name: The name of the scope. If None, the name will be derived from the calling frame. Usually the function name.
    :param state: A dictionary of extra data to log that is attached to each trace.
    :param trace_id: The trace ID to use for the scope. If None, a random ID will be generated.
    :param parent_id: The parent ID to use for the scope. If None, the parent ID will be derived from the parent scope.
    :param kwargs: Additional keyword arguments to be passed to each trace.

    """

    stack = inspect.stack(2)
    frame = stack[2]

    with Span.push(name, trace_id=trace_id, parent_id=parent_id, state=state, frame=frame, **kwargs) as scope:
        yield scope


@contextlib.contextmanager
def log_duration(level: Literal["info", "debug", "trace"] = "info", state: dict[str, Any] | None = None, **kwargs) -> Iterator[None]:
    """
    Measures the execution time of the current scope and logs it at the INFO level.
    Events [start, complete, error] are logged under the _benchmark_ property.
    Errors are logged at the ERROR level.

    :param level: The logging level to use for the duration.
    :param state: A dictionary of extra data that is attached to each log event.
    """
    if scope := Span.current():
        try:
            Span.log_event(message=f"{scope.name}: span status {scope.status}.", frame_at=0, level=TRACE_LEVEL, state=state, **kwargs)
            yield

            scope.stopwatch.stop()
            scope.status = SpanStatus.OK
            Span.log_event(message=f"{scope.name}: span status {scope.status}.", frame_at=0, level=_get_logging_level(level, scope.status), state=state, **kwargs)
        except Exception:
            scope.stopwatch.stop()
            scope.status = SpanStatus.ERROR
            Span.log_event(message=f"{scope.name}: span status {scope.status}.", frame_at=0, level=_get_logging_level(level, scope.status), state=state, **kwargs)
            raise
    else:
        raise NoActivityInScopeError("Cannot log duration because there is no span in scope.")


def _get_logging_level(level: Literal["info", "debug", "trace"], status: SpanStatus) -> int:
    match (level, status):
        case ("info", SpanStatus.OK):
            return logging.INFO
        case ("info", SpanStatus.ERROR):
            return logging.ERROR
        case ("debug", _):
            return logging.DEBUG
        case ("trace", _):
            return TRACE_LEVEL
        case _:
            raise ValueError(f"Invalid logging level: {level}")
