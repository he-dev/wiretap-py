import contextlib
import inspect
import logging
from typing import Any, Iterator, Literal

from wiretap.core import TRACE_LEVEL, SpanStatus
from wiretap.core.span import Span

# meta: Let's not repeat it twice.
DurationLevel = Literal["info", "debug", "trace"]


@contextlib.contextmanager
def begin_span(
        name: str | None = None,
        state: dict[str, Any] | None = None,
        trace_id: Any | None = None,
        parent_id: Any | None = None,
        log_duration_as: DurationLevel | None = "info",
        **kwargs
) -> Iterator[Span]:
    """
    Initializes a new span and logs its start at the TRACE level and duration at the INFO level by default.

    :param name: The name of the span. If None, the name will be derived from the calling frame. Usually the function name.
    :param state: A dictionary of extra data to log that is attached to each trace.
    :param trace_id: The trace ID to use for the span. If None, a random ID will be generated.
    :param parent_id: The parent ID to use for the span. If None, the parent ID will be derived from the parent span.
    :param log_duration_as: Whether to log the duration of the span and at which level. If None, no logging will be performed.
    :param kwargs: Additional keyword arguments to be passed to each trace.
    :returns: The newly created span.
    """

    duration_level = logging.NOTSET

    # core: Map duration level early to throw a potential exception right away and not at the end.
    if log_duration_as:
        duration_level = _map_duration_level(log_duration_as)

    stack = inspect.stack(2)
    frame = stack[2]

    with Span.push(name, trace_id=trace_id, parent_id=parent_id, state=state, frame=frame, **kwargs) as span:
        try:
            Span.log_event(
                message=f"{span.name}: {span.status}.",
                frame_at=0,
                level=TRACE_LEVEL,
                event="span_begin"
            )
            yield span
            span.stopwatch.stop()
            span.status = SpanStatus.OK
        except Exception:
            span.stopwatch.stop()
            span.status = SpanStatus.ERROR
            raise
        finally:
            if log_duration_as:
                Span.log_event(
                    message=f"{span.name}: {span.status}. Duration: {span.stopwatch.duration_ms} ms.",
                    frame_at=0,
                    level=duration_level,
                    event="span_end"
                )


def _map_duration_level(level: DurationLevel | None) -> int:
    match level:
        case "info":
            return logging.INFO
        case "debug":
            return logging.DEBUG
        case "trace":
            return TRACE_LEVEL
        case _:
            raise ValueError(f"Invalid duration level: {level}")
