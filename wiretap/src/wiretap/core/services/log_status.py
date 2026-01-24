from wiretap.core.services.log_messages import log_event
from wiretap.util.span import Span, SpanStatus, LogLevelName


class LogStatus:
    """
    A callable class that logs the status of a span at the specified log level when the span begins or ends.
    """

    def __init__(self, level: LogLevelName | None = None) -> None:
        """
        Args:
            level: The log level at which the duration event will be recorded.
        """

        self.level = level

    def __call__(self, span: Span) -> None:
        # core: When passed to on_begin the UNSET status is handled, otherwise on_end the other one.
        if span.status == SpanStatus.UNSET:
            log_event(
                message=f"Span '{span.operation}' began.",
                frame_at=0,
                level=self.level or "trace",
                event="begin_span"
            )
        else:
            log_event(
                message=f"Span '{span.operation}' ended with status '{span.status}' in {span.stopwatch.duration_ms} ms.",
                frame_at=0,
                level=self.level or "info",
                event="end_span"
            )
