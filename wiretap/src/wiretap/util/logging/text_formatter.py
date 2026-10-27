import logging
from copy import copy

from wiretap.util.activity import ActivityScope
from wiretap.meta import trim_path, FormatData


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record: logging.LogRecord):
        # meta: Adds custom properties to the record so that they can be used in the configured log format.

        activity = record.__dict__.get("activity", {})

        if not activity:
            record.activity = {
                "about": None,
                "event": None
            }
            record.trace = {
                "id": None,
                "span_id": None,
                "parent_id": None
            }
            record.source = {
                "func": None,
                "file": None,
                "line": None
            }
            record.context = {}

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

        # core: dict-render only _wiretap messages.
        record = copy(record)
        if record.__dict__.get("_wiretap", False):
            record.msg = (
                None if record.msg is None
                else str(record.msg).format_map(FormatData(record.__dict__))
            )
            record.args = ()

        return super().format(record)
