import dataclasses
import logging
import os
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable

from wiretap.meta import trim_path

# util: Type alias for convenience
JSONEntry = dict[str, Any]


@dataclasses.dataclass
class JSONMiddlewareContext:
    record: logging.LogRecord
    entry: JSONEntry
    activity_extra: dict[str, Any] | None


# meta: Using ABC because we're creating objects dynamically.
class JSONMiddleware(ABC):
    """Allows modifying the structure of the JSON entry."""

    @abstractmethod
    def __call__(self, context: JSONMiddlewareContext) -> JSONEntry: ...


class GetTimestamp:
    _get: Callable[[float], datetime]

    def __init__(self, tz: str = "utc"):
        match tz.casefold().strip():
            case "utc":
                self._get = self._utc
            case "local" | "lt":
                self._get = self._local
            case _:
                raise ValueError(f"Invalid timezone: {tz}. Only [utc|local] are supported.")

    def __call__(self, created: float) -> datetime:
        return self._get(created)

    @staticmethod
    def _utc(created: float) -> datetime:
        return datetime.fromtimestamp(created, tz=timezone.utc)

    @staticmethod
    def _local(created: float) -> datetime:
        # util: Convert from an explicit UTC instant instead of relying on tz=None as a local-time sentinel.
        return datetime.fromtimestamp(created, tz=timezone.utc).astimezone()


class AddTimestamp(JSONMiddleware):
    def __init__(self, tz: str = "utc"):
        super().__init__()
        self.get_timestamp = GetTimestamp(tz)

    def __call__(self, context: JSONMiddlewareContext) -> JSONEntry:
        return context.entry | {
            "timestamp": self.get_timestamp(context.record.created)
        }


class AddMessage(JSONMiddleware):

    def __call__(self, context: JSONMiddlewareContext) -> JSONEntry:
        return context.entry | {
            "message": context.record.getMessage(),
            "level": context.record.levelname.lower(),
        }


class AddTraceContext(JSONMiddleware):

    def __call__(self, context: JSONMiddlewareContext) -> JSONEntry:
        if extra := context.activity_extra:
            return context.entry | {
                "trace_id": extra["trace_id"],
                "span_id": extra["span_id"],
                "parent_id": extra["parent_id"],
            }
        else:
            return context.entry | {
                "trace_id": None,
                "span_id": None,
                "parent_id": None,
            }


class AddSource(JSONMiddleware):

    def __call__(self, context: JSONMiddlewareContext) -> JSONEntry:
        if context.activity_extra is None:
            return context.entry | {"source": {
                "func": context.record.funcName,
                "file": trim_path(context.record.filename),
                "line": context.record.lineno,
            }}
        else:
            return context.entry


class AddActivity(JSONMiddleware):

    def __call__(self, context: JSONMiddlewareContext) -> JSONEntry:
        if extra := context.activity_extra:
            return context.entry | {"activity": extra["activity"]}
        else:
            return context.entry | {"activity": {
                "name": None,
                "depth": None,
                "status": None,
                "duration_ms": None,
                "site": None,
            }}


class AddException(JSONMiddleware):

    def __call__(self, context: JSONMiddlewareContext) -> JSONEntry:
        if context.record.exc_info and all(context.record.exc_info):
            exc_cls, exc, exc_tb = context.record.exc_info
            return context.entry | {"exception": {
                "message": str(exc),
                "type": exc_cls.__name__,  # type: ignore
                "stack_trace": "".join(traceback.format_exception(exc_cls, exc, exc_tb))
            }}

        return context.entry


class AddEnvironmentVariable(JSONMiddleware):

    def __init__(self, names: list[str]):
        self.names = names

    def __call__(self, context: JSONMiddlewareContext) -> JSONEntry:
        def resolve(name: str) -> str:
            if name not in os.environ:
                # core: The key was never set; typo or missing deployment var.
                return "<key-not-found>"
            value = os.environ[name]
            if not value:
                # core: The key exists but holds nothing.
                return "<value-is-empty>"
            return value

        environment = {name: resolve(name) for name in self.names}
        return context.entry | {"environment": environment}
