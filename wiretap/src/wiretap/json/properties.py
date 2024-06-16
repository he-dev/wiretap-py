import logging
import os
import traceback
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol, Any

from _reusable import nth_or_default
from wiretap import tag
from wiretap.data import WIRETAP_KEY, Trace, Activity, Bag


class JSONProperty(Protocol):
    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        pass


class TimestampProperty(JSONProperty):
    def __init__(self, tz: str = "utc"):
        super().__init__()
        match tz.casefold().strip():
            case "utc":
                self.tz = datetime.now(timezone.utc).tzinfo  # timezone.utc
            case "local" | "lt":
                self.tz = datetime.now(timezone.utc).astimezone().tzinfo

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        return {
            "timestamp": datetime.fromtimestamp(record.created, tz=self.tz)
        }


class ActivityProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            bag: Bag = record.__dict__[WIRETAP_KEY]
            return {
                "activity": {
                    "name": bag.activity.name,
                    "elapsed": round(float(bag.activity.elapsed), 3),
                    "depth": bag.activity.depth,
                    "id": bag.activity.id,
                }
            }
        else:
            return {
                "activity": {
                    "name": record.funcName,
                    "elapsed": None,
                    "depth": None,
                    "id": None,
                }
            }


class PreviousProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            bag: Bag = record.__dict__[WIRETAP_KEY]
            previous: Activity | None = nth_or_default(list(bag.activity), 1)
            if previous:
                return {
                    "previous": {
                        "name": previous.name,
                        "elapsed": round(float(previous.elapsed), 3),
                        "depth": previous.depth,
                        "id": previous.id,
                    }
                }

        return {}


class SequenceProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            bag: Bag = record.__dict__[WIRETAP_KEY]
            return {
                "sequence": {
                    "name": [a.name for a in bag.activity],
                    "elapsed": [round(float(bag.activity.elapsed), 3) for a in bag.activity],
                    "id": [a.id for a in bag.activity],
                }
            }
        else:
            return {}


class TraceProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            bag: Bag = record.__dict__[WIRETAP_KEY]
            return {
                "trace": {
                    "name": bag.trace.name,
                    "message": bag.trace.message,
                    "tags": sorted(bag.trace.tags, key=lambda x: str(x) if isinstance(x, Enum) else x),
                }
            }
        else:
            return {
                "trace": {
                    "name": f":{record.levelname}",
                    "message": record.msg,
                    "tags": [tag.PLAIN],
                }
            }


class SnapshotProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            bag: Bag = record.__dict__[WIRETAP_KEY]
            return {
                "snapshot": bag.snapshot,
            }
        else:
            return {
                "snapshot": None
            }


class SourceProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            bag: Bag = record.__dict__[WIRETAP_KEY]
            if bag.activity.name == "begin":
                return {
                    "source": {
                        "file": bag.activity.frame.filename,
                        "line": bag.activity.frame.lineno,
                    }
                }
            else:
                return {}
        else:
            return {
                "source": {
                    "file": record.filename,
                    "line": record.lineno
                }
            }


class ExceptionProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if record.exc_info:
            exc_cls, exc, exc_tb = record.exc_info
            # format_exception returns a list of lines. Join it a single sing or otherwise an array will be logged.
            return {"exception": "".join(traceback.format_exception(exc_cls, exc, exc_tb))}
        else:
            return {}


class EnvironmentProperty(JSONProperty):

    def __init__(self, keys: list[str]):
        self.keys = keys

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        return {k: os.environ.get(k) for k in self.keys}
