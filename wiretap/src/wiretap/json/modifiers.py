import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Protocol, Any, runtime_checkable, Optional

from util import trim_path
from wiretap.scopes.activity_scope import ActivityEvent


@runtime_checkable
class JSONModifier(Protocol):
    """Create a single JSON property in the final JSON object."""

    def apply(self, record: logging.LogRecord, entry: dict[str, Any]) -> dict[str, Any]:
        pass


class VersionProperty(JSONModifier):

    def apply(self, record: logging.LogRecord, entry: dict[str, Any]) -> dict[str, Any]:
        return entry | {
            "version": 11
        }


class AddTimestamp(JSONModifier):
    def __init__(self, tz: str = "utc"):
        super().__init__()
        match tz.casefold().strip():
            case "utc":
                self.tz = datetime.now(timezone.utc).tzinfo  # timezone.utc
            case "local" | "lt":
                self.tz = datetime.now(timezone.utc).astimezone().tzinfo
            case _:
                raise ValueError(f"Invalid timezone: {tz}. Only [utc|local] are supported.")

    def apply(self, record: logging.LogRecord, entry: dict[str, Any]) -> dict[str, Any]:
        return entry | {
            "timestamp": datetime.fromtimestamp(record.created, tz=self.tz)
        }


class AddMessage(JSONModifier):

    def apply(self, record: logging.LogRecord, entry: dict[str, Any]) -> dict[str, Any]:
        return entry | {
            "message": record.msg,
            "level": record.levelname.lower(),
        }


class AddActivity(JSONModifier):

    def apply(self, record: logging.LogRecord, entry: dict[str, Any]) -> dict[str, Any]:
        if event := ActivityEvent.extract_or_default(record):
            return entry | {"activity": {
                "name": event.scope,
                "trace_id": event.trace_id,
                "span_id": event.span_id,
                "parent_id": event.parent_id,
                "elapsed": round(event.elapsed, 1),
            }}
        else:
            return entry | {"activity": {
                "name": record.funcName,
                "trace_id": None,
                "span_id": None,
                "parent_id": None,
                "elapsed": None,
            }}


class AddSource(JSONModifier):

    def apply(self, record: logging.LogRecord, entry: dict[str, Any]) -> dict[str, Any]:
        # if not logging.getLogger(__name__).isEnabledFor(logging.DEBUG):
        #    return entry

        if event := ActivityEvent.extract_or_default(record):
            return entry | {"source": {
                "func": event.frame.function,
                "file": trim_path(event.frame.filename),
                "line": event.frame.lineno
            }}
        else:
            return entry | {"source": {
                "func": record.funcName,
                "file": record.filename,
                "line": record.lineno,
            }}


class AddProperties(JSONModifier):

    def __init__(self, names: Optional[list[str]] = None):
        self.names = names or ["src"]

    def apply(self, record: logging.LogRecord, entry: dict[str, Any]) -> dict[str, Any]:
        if event := ActivityEvent.extract_or_default(record):
            return entry | {"properties": event.state}
        else:
            return entry | {"properties": {}}


class AddException(JSONModifier):

    def apply(self, record: logging.LogRecord, entry: dict[str, Any]) -> dict[str, Any]:
        if record.exc_info and all(record.exc_info):
            exc_cls, exc, exc_tb = record.exc_info
            # note: format_exception returns a list of lines. Join it a single sing or otherwise an array will be logged.
            # entry["trace"]["event"] = exc_cls.__name__
            return entry | {"exception": {
                "message": str(exc),
                "type": exc_cls.__name__,  # type: ignore
                "stack_trace": "".join(traceback.format_exception(exc_cls, exc, exc_tb))
            }}

        return entry


class AddEnvironmentVariables(JSONModifier):

    def __init__(self, names: list[str]):
        self.names = names

    def apply(self, record: logging.LogRecord, entry: dict[str, Any]) -> dict[str, Any] | None:
        env = {k: os.environ.get(k) for k in self.names}
        return entry | {"environment": env} if entry else env
