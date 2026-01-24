import contextlib
import inspect
from typing import Any, Iterator, Callable

from wiretap.util.span import Span, SpanStatus


@contextlib.contextmanager
def begin_span(
        name: str | None = None,
        state: dict[str, Any] | None = None,
        trace_id: Any | None = None,
        parent_id: Any | None = None,
        on_begin: Callable[[Span], None] | None = None,
        on_end: Callable[[Span], None] | None = None,
        **kwargs
) -> Iterator[Span]:
    """
    Initializes a new span and logs its start at the TRACE level and duration at the INFO level by default.

    Args:
        name: The name of the span. If None, the name will be derived from the calling frame. Usually the function name.
        state: A dictionary of extra data to log that is attached to each trace.
        trace_id: The trace ID to use for the span. If None, a random ID will be generated.
        parent_id: The parent ID to use for the span. If None, the parent ID will be derived from the parent span.
        on_begin: A callback to be called when the span would log an event.
        on_end: A callback to be called when the span would log an event.
        kwargs: Additional keyword arguments to be passed to each trace.

    Returns:
        The newly created span.
    """

    # util: Use defaults for convenience.
    on_begin = on_begin or (lambda _: None)
    on_end = on_end or (lambda _: None)

    stack = inspect.stack(2)
    frame = stack[2]

    with Span(name, state=state, trace_id=trace_id, parent_id=parent_id, frame=frame, **kwargs).push() as span:
        try:
            on_begin(span)
            yield span
            span.stopwatch.stop()
            span.status = SpanStatus.OK
        except Exception:
            span.stopwatch.stop()
            span.status = SpanStatus.ERROR
            raise
        finally:
            on_end(span)


class SpanHooks:
    """Allows attaching multiple callbacks to span events."""

    def __init__(self, *callbacks: Callable[[Span], None]):
        self.callbacks = callbacks

    def __call__(self, span: Span) -> None:
        for cb in self.callbacks:
            cb(span)
