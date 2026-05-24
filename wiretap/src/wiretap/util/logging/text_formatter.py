import logging
from typing import Any

from wiretap.util.activity_scope import ActivityScope
from wiretap.util.span import SpanEvent, Span
from wiretap.meta import trim_path


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record: logging.LogRecord):
        # meta: Adds custom properties to the record so that they can be used in the configured log format.

        include_source = logging.getLogger(__name__).isEnabledFor(logging.DEBUG)

        # core: This is a wiretap record.
        if state_items := record.__dict__.get("wiretap", None):
            record.activity = state_items.get("activity", None)
            record.activity_status = state_items.get("activity_status", None)
            record.activity_role = state_items.get("activity_role", None)
            record.message = record.msg
            record.elapsed_ms = state_items.get("elapsed_ms", None)
            record.indent = self.indent * state_items.get("depth", 0)
            record.properties = stringify_deep(state_items)
            record.source = "?"
            return super().format(record)

        # core: This is a native logging record inside a wiretap's activity.'
        if scope := ActivityScope.current():
            state_items = scope.state_items
            record.activity = state_items.get("activity", None)
            record.activity_status = state_items.get("activity_status", None)
            record.activity_role = state_items.get("activity_role", None)
            record.message = record.msg
            record.elapsed_ms = state_items.get("elapsed_ms", None)
            record.indent = self.indent * state_items.get("depth", 0)
            record.properties = stringify_deep(state_items)
            record.source = "?"
            return super().format(record)

        # core: This is a native logging record outside a wiretap's span.
        record.activity = record.funcName
        record.activity_status = None
        record.activity_role = "Buzz"
        record.message = record.msg
        record.elapsed_ms = -1
        record.indent = ""
        record.source = {
            "func": record.funcName,
            "file": trim_path(record.filename),
            "line": record.lineno
        } if include_source else "off"
        record.properties = None

        return super().format(record)

        # core: This is a native wiretap record.
        if event := SpanEvent.extract_from(record):
            record.operation = event.operation
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
        if span := Span.current():
            event = SpanEvent(span)
            record.operation = event.operation
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
        record.operation = record.funcName
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


def stringify_deep(obj: dict | Any) -> dict | str:
    match obj:
        case dict():
            return {k: stringify_deep(v) for k, v in obj.items()}
        case _:
            return str(obj)
