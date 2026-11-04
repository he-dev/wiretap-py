import logging
from copy import copy

from wiretap.meta import trim_path
from wiretap.util.buzz.render_message import render_message


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record: logging.LogRecord):
        # meta: Adds custom properties to the record so that they can be used in the configured log format.

        record = copy(record)
        record.__dict__.setdefault("fixme", [])
        record.__dict__.setdefault("aboutme", [])

        plot = record.__dict__.get("plot", {})

        if not plot:
            record.__dict__.setdefault("plot", {
                "about": None,
                "event": None,
                "depth": 0,
            })
            record.__dict__.setdefault("trace", {
                "id": None,
                "span_id": None,
                "parent_id": None,
            })
            record.__dict__.setdefault("context", {})

        record.indent = self.indent * plot.get("depth", 0)
        include_source = (
                logging.getLogger(record.name).isEnabledFor(logging.DEBUG)
                or plot.get("event") == "ZERO"
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

        # core: dict-render only _wiretap messages.
        record.msg = render_message(record)
        record.args = ()
        return super().format(record)
