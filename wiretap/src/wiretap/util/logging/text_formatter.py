import logging
from typing import Any

from wiretap.util import span
from wiretap.util.activity_scope import ActivityScope
from wiretap.meta import trim_path


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record: logging.LogRecord):
        # meta: Adds custom properties to the record so that they can be used in the configured log format.

        include_source = logging.getLogger(__name__).isEnabledFor(logging.DEBUG)

        # core: Try wiretap record first.
        scope = record.__dict__.get("wiretap", {})
        if not scope:
            # core: Try native logging record inside a wiretap's activity'.
            if activity := ActivityScope.current():
                scope = activity.to_extra(None, None)

        # note: There is a scope!
        if scope:
            record.indent = self.indent * scope["activity"]["depth"]
            record.message = record.msg
            record.activity = scope.get("activity", None)
            record.span = {
                "trace_id": scope.get("trace_id", None),
                "span_id": scope.get("span_id", None),
                "parent_id": scope.get("parent_id", None),
            }
            record.state = scope["state"]
            record.source = scope["source"] if include_source else None
            return super().format(record)

        # core: This is a native logging record outside a wiretap's span.
        record.indent = ""
        record.message = record.msg
        record.activity = {
            "name": record.funcName,
            "tags": None,
            "elapsed_ms": None
        }
        record.span = None
        record.state = None
        record.source = {
            "func": record.funcName,
            "file": trim_path(record.filename),
            "line": record.lineno
        } if include_source else None

        return super().format(record)


def stringify_deep(obj: dict | Any) -> dict | str:
    match obj:
        case dict():
            return {k: stringify_deep(v) for k, v in obj.items()}
        case _:
            return str(obj)
