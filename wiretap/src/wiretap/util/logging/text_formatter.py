import logging

from wiretap.core.span import SpanEvent, Span
from wiretap.util import trim_path

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {scope}: {trace} | {elapsed:0.3f} sec | {message} | {trace_state}, {trace_tags}"


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record: logging.LogRecord):

        include_source = logging.getLogger(__name__).isEnabledFor(logging.DEBUG)

        event = record.__dict__.get(SpanEvent.KEY, None)
        if not event:
            if scope := Span.current():
                event = SpanEvent(scope)

        if event:
            record.span_name = event.name
            record.indent = 1  # self.indent * activity.scope.depth
            record.properties = stringify_deep(event.state)
            record.span = {
                "trace_id": event.trace_id,
                "span_id": event.span_id,
                "parent_id": event.parent_id,
                "elapsed": event.stopwatch.elapsed_ms if event.stopwatch.is_running else None,
                "duration": None if event.stopwatch.is_running else round(event.stopwatch.duration_ms, 1),
                "status": event.status.value,
            }
            record.source = {
                "func": event.frame.function if event.frame else record.funcName,
                "file": trim_path(event.frame.filename) if event.frame else trim_path(record.filename),
                "line": event.frame.lineno if event.frame else record.lineno
            } if include_source else "off"

        else:
            record.span_name = record.funcName
            record.message = record.msg
            record.indent = self.indent
            record.source = {
                "func": record.funcName,
                "file": trim_path(record.filename),
                "line": record.lineno
            } if include_source else "off"
            record.properties = None
            record.span = None

        return super().format(record)


def stringify_deep(obj: dict) -> dict | str:
    match obj:
        case dict():
            return {k: stringify_deep(v) for k, v in obj.items()}
        case _:
            return str(obj)
