import logging

from wiretap.util.activity import ActivityScope
from wiretap.meta import trim_path


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record: logging.LogRecord):
        # meta: Adds custom properties to the record so that they can be used in the configured log format.

        include_source = logging.getLogger(__name__).isEnabledFor(logging.DEBUG)

        # core: This is a native logging record, but inside a wiretap's span.
        if activity := ActivityScope.get_current():
            record.operation = event.operation
            record.indent = self.indent * event.depth
            record.properties = stringify_deep(event.state)
            record.span = {} | {
                "trace_id": event.trace_id,
                "span_id": event.span_id,
                "parent_id": event.parent_id,
                "status": event.status.value,
            } | event.stopwatch.move_next(iso=True)
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


def stringify_deep(obj: dict) -> dict | str:
    match obj:
        case dict():
            return {k: stringify_deep(v) for k, v in obj.items()}
        case _:
            return str(obj)
