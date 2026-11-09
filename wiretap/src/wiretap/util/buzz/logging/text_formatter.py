import logging
from copy import copy

from wiretap.meta import trim_path
from wiretap.util.buzz.render_message import render_message


class TextFormatter(logging.Formatter):

    def __init__(self, *args, indent: str = ".", **kwargs):
        super().__init__(*args, **kwargs)
        self.indent = indent

    def format(self, record: logging.LogRecord):
        # meta: Adds custom properties to the record so that they can be used in the configured log format.

        record = copy(record)
        activity = dict(record.__dict__.get("activity") or {})
        activity.setdefault("about", None)
        activity.setdefault("event", None)
        activity.setdefault("depth", 0)
        record.__dict__["activity"] = activity
        record.__dict__["trace"] = record.__dict__.get("trace") or {
            "id": None,
            "span_id": None,
            "parent_id": None,
        }
        record.__dict__.setdefault("properties", {})
        defaults = self._style._defaults or {}
        record.__dict__["properties"] = {
            **defaults.get("properties", {}),
            **(record.__dict__.get("properties") or {}),
        }

        record.indent = self.indent * activity.get("depth", 0)
        is_debug = logging.getLogger(record.name).isEnabledFor(logging.DEBUG)
        is_last = activity.get("event") == "LAST"
        is_error = record.levelno >= logging.ERROR

        if (is_debug and is_last) or is_error:
            record.source = {
                "func": record.funcName,
                "file": trim_path(record.filename),
                "line": record.lineno
            }
        else:
            record.__dict__.setdefault("source", {})

        # core: dict-render only _format_map messages.
        record.msg = render_message(record)
        record.args = ()
        return super().format(record)
