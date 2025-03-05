import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Protocol, Any

from wiretap.scopes import logger_scope, logger_trace


class JSONProperty(Protocol):
    def emit(self, entry: dict[str, Any], record: logging.LogRecord) -> dict[str, Any]:
        pass


class TimestampProperty(JSONProperty):
    def __init__(self, tz: str = "utc"):
        super().__init__()
        match tz.casefold().strip():
            case "utc":
                self.tz = datetime.now(timezone.utc).tzinfo  # timezone.utc
            case "local" | "lt":
                self.tz = datetime.now(timezone.utc).astimezone().tzinfo

    def emit(self, entry: dict[str, Any], record: logging.LogRecord) -> dict[str, Any]:
        return entry | {
            "timestamp": datetime.fromtimestamp(record.created, tz=self.tz)
        }


class ScopeProperty(JSONProperty):
    from wiretap.data import LoggerPath

    def emit(self, entry: dict[str, Any], record: logging.LogRecord) -> dict[str, Any]:
        scope = logger_scope(record)
        if scope:
            entry["scope"] = {
                "id": self.__class__.LoggerPath(scope, lambda x: x.id),
                "name": self.__class__.LoggerPath(scope, lambda x: x.name),
                "elapsed": scope.elapsed.current,
                "depth": scope.depth,
            }
        else:
            entry["scope"] = {
                "id": None,
                "name": record.funcName,
                "elapsed": None,
                "depth": None,
            }

        return entry


class TraceProperty(JSONProperty):

    def emit(self, entry: dict[str, Any], record: logging.LogRecord) -> dict[str, Any]:
        trace = logger_trace(record)
        if trace:
            entry["trace"] = {
                "name": trace.name,
                "level": record.levelname.lower(),
                "message": trace.message,
                "state": trace.state,
                "tags": sorted(trace.tags),
            }
        else:
            entry["trace"] = {
                "name": record.levelname.lower(),
                "level": record.levelname.lower(),
                "message": record.msg,
                "state": {
                    "func": record.funcName,
                    "file": record.filename,
                    "line": record.lineno
                },
                "tags": ["plain"]
            }

        return entry


class ExceptionProperty(JSONProperty):

    def emit(self, entry: dict[str, Any], record: logging.LogRecord) -> dict[str, Any]:
        if record.exc_info:
            exc_cls, exc, exc_tb = record.exc_info
            # format_exception returns a list of lines. Join it a single sing or otherwise an array will be logged.
            entry["message"] = str(exc)
            entry["trace"] = entry["trace"]["state"] | {
                "exception": exc_cls.__name__,  # type: ignore
                "stack_trace": "".join(traceback.format_exception(exc_cls, exc, exc_tb))
            }

        return entry


class EnvironmentProperty(JSONProperty):

    def __init__(self, names: list[str]):
        self.names = names

    def emit(self, entry: dict[str, Any], record: logging.LogRecord) -> dict[str, Any] | None:
        scope = logger_scope(record)
        trace = logger_trace(record)
        # Log this only for the very first feed.
        if scope and not scope.parent and trace and trace.name == "begin":
            return entry | {"environment": {k: os.environ.get(k) for k in self.names}}

        return entry
