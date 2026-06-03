import dataclasses
import logging
import os
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

from wiretap.util.activity_scope import ActivityScope
from wiretap.meta import trim_path

# util: Type alias for convenience
JSONEntry = dict[str, Any]


@dataclasses.dataclass
class ComposeJSONContext:
    record: logging.LogRecord

    @property
    def scope(self) -> dict[str, Any] | None:
        if data := getattr(self.record, "wiretap", None):
            return data

        if scope := ActivityScope.current():
            return scope.to_extra(status=None, state=None)

        return None

    entry: JSONEntry


# meta: Using ABC because we're creating objects dynamically.
class ComposeJSON(ABC):
    """Allows modifying the structure of the JSON entry."""

    @abstractmethod
    def __call__(self, context: ComposeJSONContext) -> JSONEntry: ...


class AddTimestamp(ComposeJSON):
    def __init__(self, tz: str = "utc"):
        super().__init__()
        match tz.casefold().strip():
            case "utc":
                self.tz = datetime.now(timezone.utc).tzinfo  # timezone.utc
            case "local" | "lt":
                self.tz = datetime.now(timezone.utc).astimezone().tzinfo
            case _:
                raise ValueError(f"Invalid timezone: {tz}. Only [utc|local] are supported.")

    def __call__(self, context: ComposeJSONContext) -> JSONEntry:
        return context.entry | {
            "timestamp": datetime.fromtimestamp(context.record.created, tz=self.tz)
        }


class AddMessage(ComposeJSON):

    def __call__(self, context: ComposeJSONContext) -> JSONEntry:
        return context.entry | {
            "message": context.record.getMessage(),
            "level": context.record.levelname.lower(),
        }


class AddSpan(ComposeJSON):

    def __call__(self, context: ComposeJSONContext) -> JSONEntry:
        if scope := context.scope:

            return context.entry | {
                "trace_id": scope["trace_id"],
                "span_id": scope["span_id"],
                "parent_id": scope["parent_id"],
            }
        else:
            return context.entry | {
                "trace_id": None,
                "span_id": None,
                "parent_id": None,
            }


class AddSource(ComposeJSON):

    def __call__(self, context: ComposeJSONContext) -> JSONEntry:
        if scope := context.scope:
            return context.entry | {"source": scope["source"]}
        else:
            return context.entry | {"source": {
                "func": context.record.funcName,
                "file": trim_path(context.record.filename),
                "line": context.record.lineno,
            }}


class AddActivity(ComposeJSON):

    def __call__(self, context: ComposeJSONContext) -> JSONEntry:
        if scope := context.scope:
            return context.entry | {"activity": scope["activity"]}
        else:
            return context.entry | {"activity": {}}


class AddException(ComposeJSON):

    def __call__(self, context: ComposeJSONContext) -> JSONEntry:
        if context.record.exc_info and all(context.record.exc_info):
            exc_cls, exc, exc_tb = context.record.exc_info
            # note: format_exception returns a list of lines. Join it a single sing or otherwise an array will be logged.
            # entry["trace"]["event"] = exc_cls.__name__
            return context.entry | {"exception": {
                "message": str(exc),
                "type": exc_cls.__name__,  # type: ignore
                "stack_trace": "".join(traceback.format_exception(exc_cls, exc, exc_tb))
            }}

        return context.entry


class AddEnvironmentVariables(ComposeJSON):

    def __init__(self, names: list[str]):
        self.names = names

    def __call__(self, context: ComposeJSONContext) -> JSONEntry:
        env = {k: os.environ.get(k) for k in self.names}
        return context.entry | {"environment": env} if env else context.entry
