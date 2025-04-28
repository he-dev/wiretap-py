import logging
import traceback
from datetime import datetime, timezone
from typing import Protocol, Any, runtime_checkable

from tools.chain_path import ChainPath
from wiretap.scopes import TelemetryItem


@runtime_checkable
class JSONMiddleware(Protocol):
    """Create a single JSON property in the final JSON object."""
    def emit(self, record: logging.LogRecord, entry: dict[str, Any]) -> dict[str, Any]:
        pass


class TimestampMiddleware(JSONMiddleware):
    def __init__(self, tz: str = "utc"):
        super().__init__()
        match tz.casefold().strip():
            case "utc":
                self.tz = datetime.now(timezone.utc).tzinfo  # timezone.utc
            case "local" | "lt":
                self.tz = datetime.now(timezone.utc).astimezone().tzinfo
            case _:
                raise ValueError(f"Invalid timezone: {tz}. Only [utc|local] are supported.")

    def emit(self, record: logging.LogRecord, entry: dict[str, Any]) -> dict[str, Any]:
        return entry | {
            "timestamp": datetime.fromtimestamp(record.created, tz=self.tz)
        }


class ScopeMiddleware(JSONMiddleware):
    # from wiretap.scopes import TelemetryPath

    def emit(self, record: logging.LogRecord, entry: dict[str, Any]) -> dict[str, Any]:
        telemetry = TelemetryItem.from_record_or_scope(record)
        if telemetry and telemetry.scope:
            entry["scope"] = {
                "id": ChainPath(telemetry.scope, lambda x: x.id),
                "name": ChainPath(telemetry.scope, lambda x: x.name),
                "elapsed": telemetry.scope.elapsed.current,
                "depth": telemetry.scope.depth,
            }
        else:
            entry["scope"] = {
                "id": None,
                "name": record.funcName,
                "elapsed": None,
                "depth": None,
            }

        return entry


class TraceMiddleware(JSONMiddleware):

    def emit(self, record: logging.LogRecord, entry: dict[str, Any]) -> dict[str, Any]:
        scope, trace = TelemetryItem.from_record_or_scope(record).properties
        if scope and trace:
            entry["trace"] = {
                "name": trace.name,
                "level": {
                    "name": record.levelname.lower(),
                    "value": record.levelno
                },
                "message": trace.message,
                "dump": trace.dump,
                "tags": trace.tags,
            }
        else:
            entry["trace"] = {
                "name": record.levelname.lower(),
                "level": {
                    "name": record.levelname.lower(),
                    "value": record.levelno
                },
                "message": record.msg,
                "dump": {
                    "func": record.funcName,
                    "file": record.filename,
                    "line": record.lineno
                },
                "tags": ["plain"]
            }

        return entry


class ExceptionMiddleware(JSONMiddleware):

    def emit(self, record: logging.LogRecord, entry: dict[str, Any]) -> dict[str, Any]:
        if record.exc_info and all(record.exc_info):
            exc_cls, exc, exc_tb = record.exc_info
            # format_exception returns a list of lines. Join it a single sing or otherwise an array will be logged.
            entry["message"] = str(exc)
            # entry["trace"]["event"] = exc_cls.__name__
            entry["trace"]["dump"] |= {
                "type": exc_cls.__name__,  # type: ignore
                "stack_trace": "".join(traceback.format_exception(exc_cls, exc, exc_tb))
            }

        return entry


class EnvironmentMiddleware(JSONMiddleware):

    def __init__(self, names: list[str]):
        self.names = names

    def emit(self, record: logging.LogRecord, entry: dict[str, Any]) -> dict[str, Any] | None:
        telemetry = TelemetryItem.from_record_or_scope(record)
        # Log this only for the very first feed.
        # if telemetry and not scope.parent and trace and trace.name == "begin":
        #  return entry | {"environment": {k: os.environ.get(k) for k in self.names}}

        return entry
