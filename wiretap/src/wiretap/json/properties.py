import logging
import os
import traceback
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol, Any

from _reusable import nth_or_default, Node
from wiretap import current_activity
from wiretap.data import WIRETAP_KEY, Activity, Entry


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
            entry: Entry = record.__dict__[WIRETAP_KEY]
            return {
                "activity": {
                    "func": entry.activity.func,
                    "name": entry.activity.name,
                    "elapsed": float(entry.activity.elapsed),
                    "depth": entry.activity.depth,
                    "id": entry.activity.id,
                }
            }
        else:
            node: Node | None = current_activity.get()
            return {
                "activity": {
                    "func": node.value.func if node else record.funcName,
                    "name": node.value.name if node else record.funcName,
                    "elapsed": float(node.value.elapsed) if node else None,
                    "depth": node.value.depth if node else None,
                    "id": node.value.id if node else None,
                }
            }


class PreviousProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            entry: Entry = record.__dict__[WIRETAP_KEY]
            previous: Activity | None = nth_or_default(list(entry.activity), 1)
            if previous:
                return {
                    "previous": {
                        "func": previous.func,
                        "name": previous.name,
                        "elapsed": float(previous.elapsed),
                        "depth": previous.depth,
                        "id": previous.id,
                    }
                }

        return {}


class SequenceProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            entry: Entry = record.__dict__[WIRETAP_KEY]
            return {
                "sequence": {
                    "name": [a.name for a in entry.activity],
                    "elapsed": [float(entry.activity.elapsed) for a in entry.activity],
                    "id": [a.id for a in entry.activity],
                }
            }
        else:
            return {}


class CorrelationProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            entry: Entry = record.__dict__[WIRETAP_KEY]
            return {
                "correlation": {
                    # "id": [a.id for a in entry.activity][-1]
                    "id": entry.activity.correlation.id,
                    "type": entry.activity.correlation.type,
                }
            }
        else:
            node: Node | None = current_activity.get()
            if node:
                return {
                    "correlation": {
                        # "id": [a.id for a in entry.activity][-1]
                        "id": node.value.correlation.id,
                        "type": node.value.correlation.type,
                    }
                }
            else:
                return {}


class TraceProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            entry: Entry = record.__dict__[WIRETAP_KEY]
            return {
                "trace": {
                    "code": entry.trace.code,
                    "name": entry.trace.name,
                }
            }
        else:
            return {
                "trace": {
                    "code": "plain",
                    "name": record.levelname.lower()
                }
            }


class MessageProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            entry: Entry = record.__dict__[WIRETAP_KEY]
            return {
                "message": entry.trace.message
            }
        else:
            return {
                "message": record.msg
            }


class ContextProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            entry: Entry = record.__dict__[WIRETAP_KEY]
            return {
                "context": entry.activity.body,
            }
        else:
            return {
                "context": {}
            }


class BodyProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            entry: Entry = record.__dict__[WIRETAP_KEY]
            return {
                "body": entry.body,
            }
        else:
            return {
                "body": {}
            }


class TagsProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            entry: Entry = record.__dict__[WIRETAP_KEY]
            return {
                "tags": sorted(entry.tags | (entry.activity.tags or set())),
            }
        else:
            return {
                "tags": []
            }


class SourceProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            entry: Entry = record.__dict__[WIRETAP_KEY]
            if entry.trace.code == "begin":
                return {
                    "source": {
                        "func": entry.activity.func,
                        "file": entry.activity.frame.filename,
                        "line": entry.activity.frame.lineno,
                    }
                }
            else:
                return {}
        else:
            return {
                "source": {
                    "func": record.funcName,
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

    def __init__(self, names: list[str]):
        self.names = names

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        return {"environment": {k: os.environ.get(k) for k in self.names}}
