import logging
from copy import copy

from wiretap.meta import trim_path
from wiretap.util.buzz.render_message import render_message


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record: logging.LogRecord):
        # meta: Adds custom properties to the record so that they can be used in the configured log format.

        record = copy(record)
        activity = dict(record.__dict__.get("activity") or {})
        activity.setdefault("about", None)
        activity.setdefault("event", None)
        activity.setdefault("channel", None)
        activity.setdefault("depth", 0)
        record.__dict__["activity"] = activity
        record.__dict__["trace"] = record.__dict__.get("trace") or {
            "id": None,
            "span_id": None,
            "parent_id": None,
        }
        record.__dict__.setdefault("properties", {})

        record.indent = self.indent * activity.get("depth", 0)
        include_source = (
                logging.getLogger(record.name).isEnabledFor(logging.DEBUG)
                or activity.get("event") == "ZERO"
                or record.levelno >= logging.ERROR
        )

        if include_source:
            record.source = {
                "func": record.funcName,
                "file": trim_path(record.filename),
                "line": record.lineno
            }
        else:
            record.__dict__.setdefault("source", {
                "func": None,
                "file": None,
                "line": None,
            })

        # core: dict-render only _format_map messages.
        record.msg = render_message(record)
        record.args = ()
        return super().format(record)
