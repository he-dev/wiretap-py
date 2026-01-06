import contextlib
import inspect
import logging
from typing import Any, Iterator, Literal, Callable

from wiretap.core import TRACE_LEVEL, SpanStatus
from wiretap.core.span import Span

# meta: Let's not repeat it twice.
DurationLevel = Literal["info", "debug", "trace", "off"]


@contextlib.contextmanager
def begin_span(
        name: str | None = None,
        state: dict[str, Any] | None = None,
        trace_id: Any | None = None,
        parent_id: Any | None = None,
        on_finally: list[Callable[[Span], None]] | None = None,
        **kwargs
) -> Iterator[Span]:
    """
    Initializes a new span and logs its start at the TRACE level and duration at the INFO level by default.

    Args:
        name: The name of the span. If None, the name will be derived from the calling frame. Usually the function name.
        state: A dictionary of extra data to log that is attached to each trace.
        trace_id: The trace ID to use for the span. If None, a random ID will be generated.
        parent_id: The parent ID to use for the span. If None, the parent ID will be derived from the parent span.
        on_finally: A callback to be called after the span is finished.
        kwargs: Additional keyword arguments to be passed to each trace.

    Returns:
        The newly created span.
    """

    stack = inspect.stack(2)
    frame = stack[2]

    with Span.push(name, trace_id=trace_id, parent_id=parent_id, state=state, frame=frame, **kwargs) as span:
        try:
            Span.log_event(
                message=f"{span.name}: {span.status}.",
                frame_at=0,
                level="trace",
                event="begin_span"
            )
            yield span
            span.stopwatch.stop()
            span.status = SpanStatus.OK
        except Exception:
            span.stopwatch.stop()
            span.status = SpanStatus.ERROR
            raise
        finally:
            for callback in [c for c in (on_finally or []) if c is not None]:
                callback(span)
