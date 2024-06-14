import logging
import traceback
from enum import Enum
from functools import reduce
from typing import Any
from datetime import datetime, timezone

from wiretap import tag
from _reusable import nth_or_default
from wiretap.data import Activity, TRACE_KEY, Trace


class TimestampField(logging.Filter):
    def __init__(self, tz: str = "utc"):
        super().__init__()
        match tz.casefold().strip():
            case "utc":
                self.tz = datetime.now(timezone.utc).tzinfo  # timezone.utc
            case "local" | "lt":
                self.tz = datetime.now(timezone.utc).astimezone().tzinfo

    def filter(self, record: logging.LogRecord) -> bool:
        setattr(record, "$timestamp", datetime.fromtimestamp(record.created, tz=self.tz))
        return True


class ActivityField(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        if TRACE_KEY in record.__dict__:
            trace: Trace = record.__dict__[TRACE_KEY]
            record.__dict__["$activity"] = {
                "elapsed": round(float(trace.activity.elapsed), 3),
                "id": trace.activity.id,
                "name": trace.activity.name,
                "depth": trace.activity.depth
            }
        else:
            record.__dict__["$activity"] = {
                "elapsed": None,
                "id": None,
                "name": record.funcName,
                "depth": None
            }

        return True


class PreviousField(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        if TRACE_KEY in record.__dict__:
            trace: Trace = record.__dict__[TRACE_KEY]
            previous: Activity | None = nth_or_default(list(trace.activity), 1)
            if previous:
                record.__dict__["$previous"] = {
                    "elapsed": round(float(previous.elapsed), 3),
                    "id": previous.id,
                    "name": previous.name,
                    "depth": previous.depth
                }

        return True


class SequenceField(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        if TRACE_KEY in record.__dict__:
            trace: Trace = record.__dict__[TRACE_KEY]
            record.__dict__["$sequence"] = {
                "elapsed": [round(float(trace.activity.elapsed), 3) for a in trace.activity],
                "id": [a.id for a in trace.activity],
                "name": [a.name for a in trace.activity]
            }

        return True


class TraceField(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        if TRACE_KEY in record.__dict__:
            trace: Trace = record.__dict__[TRACE_KEY]
            record.__dict__["$trace"] = {
                "name": trace.name,
                "snapshot": trace.snapshot,
                "tags": sorted(trace.tags, key=lambda x: str(x) if isinstance(x, Enum) else x),
                "message": trace.message,
            }
        else:
            record.__dict__["$trace"] = {
                "name": f":{record.levelname}",
                "snapshot": None,
                "tags": [tag.PLAIN],
                "message": record.msg,
            }

        return True


class SourceField(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        if TRACE_KEY in record.__dict__:
            trace: Trace = record.__dict__[TRACE_KEY]
            record.__dict__["$source"] = {
                "file": trace.activity.frame.filename,
                "line": trace.activity.frame.lineno,
            }
        else:
            record.__dict__["$source"] = {
                "file": record.filename,
                "line": record.lineno
            }

        return True


class ExceptionField(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info:
            exc_cls, exc, exc_tb = record.exc_info
            # format_exception return a list of lines. Join it a single sing or otherwise an array will be logged.
            record.__dict__["$exception"] = "".join(traceback.format_exception(exc_cls, exc, exc_tb))

        return True


class IndentField(logging.Filter):

    def __init__(self, char: str = "."):
        super().__init__()
        self.char = char

    def filter(self, record: logging.LogRecord) -> bool:
        setattr(record, "indent", self.char)
        if TRACE_KEY in record.__dict__:
            trace: Trace = record.__dict__[TRACE_KEY]
            setattr(record, "indent", self.char * trace.activity.depth)

        return True


class ConstField(logging.Filter):
    def __init__(self, mapping: dict[str, Any]):
        super().__init__()
        self.mapping = mapping

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in self.mapping.items():
            setattr(record, key, value)
        return True


class TemplateField(logging.Filter):

    def __init__(self, mapping: dict[str, str]):
        super().__init__()
        self.mapping = mapping

    def filter(self, record: logging.LogRecord) -> bool:
        # Map each field from the current record to a custom name from the mapping.
        for key, selector in self.mapping.items():
            value = reduce(lambda p, k: p[k], selector.split("."), record.__dict__)
            record.__dict__[key] = value

        return True
