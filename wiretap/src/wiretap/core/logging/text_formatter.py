import logging

from wiretap.core.span import SpanEvent, Span
from wiretap.util import trim_path


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record: logging.LogRecord):

        include_source = logging.getLogger(__name__).isEnabledFor(logging.DEBUG)

        # event: SpanEvent | None = record.__dict__.get(SpanEvent.KEY, None)

        # core: This is a native wiretap record.
        event: SpanEvent | None = record.__dict__.get(SpanEvent.KEY, None)
        if event:
            record.span_name = event.name
            record.indent = self.indent * event.depth
            record.properties = stringify_deep(event.state)
            record.span = {} | {
                "trace_id": event.trace_id,
                "span_id": event.span_id,
                "parent_id": event.parent_id,
                "status": event.status.value,
            } | event.stopwatch.to_dict(iso=True)
            record.source = {
                "func": event.frame.function if event.frame else record.funcName,
                "file": trim_path(event.frame.filename) if event.frame else trim_path(record.filename),
                "line": event.frame.lineno if event.frame else record.lineno
            } if include_source else "off"

            return super().format(record)

        # core: This is a native logging record, but inside a wiretap's span.
        span: Span | None = Span.current()
        if span:
            event = SpanEvent(span)
            record.span_name = event.name
            record.indent = self.indent * event.depth
            record.properties = stringify_deep(event.state)
            record.span = {} | {
                "trace_id": event.trace_id,
                "span_id": event.span_id,
                "parent_id": event.parent_id,
                "status": event.status.value,
            } | event.stopwatch.to_dict(iso=True)
            record.source = {
                "func": record.funcName,
                "file": trim_path(record.filename),
                "line": record.lineno
            } if include_source else "off"

            return super().format(record)

        # core: This is a native logging record, but stand-alone.
        record.span_name = record.funcName
        record.message = record.msg
        record.indent = ""
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
