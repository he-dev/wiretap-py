import dataclasses
import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Protocol, Any, runtime_checkable, Optional

from wiretap.core.activity_scope import ActivityEvent, ActivityScope
from wiretap.util import trim_path

JsonEntry = dict[str, Any]


@dataclasses.dataclass
class JsonModifierContext:
    record: logging.LogRecord

    @property
    def event(self) -> ActivityEvent | None:
        if event := self.record.__dict__.get(ActivityEvent.KEY, None):
            return event
        else:
            if scope := ActivityScope.peek():
                return ActivityEvent(scope)
        return None

    entry: JsonEntry


@runtime_checkable
class JsonModifier(Protocol):
    """Create a single JSON property in the final JSON object."""

    def apply(self, context: JsonModifierContext) -> JsonEntry: ...


class AddTimestamp(JsonModifier):
    def __init__(self, tz: str = "utc"):
        super().__init__()
        match tz.casefold().strip():
            case "utc":
                self.tz = datetime.now(timezone.utc).tzinfo  # timezone.utc
            case "local" | "lt":
                self.tz = datetime.now(timezone.utc).astimezone().tzinfo
            case _:
                raise ValueError(f"Invalid timezone: {tz}. Only [utc|local] are supported.")

    def apply(self, context: JsonModifierContext) -> JsonEntry:
        return context.entry | {
            "timestamp": datetime.fromtimestamp(context.record.created, tz=self.tz)
        }


class AddMessage(JsonModifier):

    def apply(self, context: JsonModifierContext) -> JsonEntry:
        return context.entry | {
            "message": context.record.msg,
            "level": context.record.levelname.lower(),
        }


class AddActivity(JsonModifier):

    def apply(self, context: JsonModifierContext) -> JsonEntry:
        if event := context.event:
            return context.entry | {"activity": {
                "name": event.scope,
                "elapsed": round(event.elapsed, 1),
                "trace_id": event.trace_id,
                "span_id": event.span_id,
                "parent_id": event.parent_id,
            }}
        else:
            return context.entry | {"activity": {
                "name": context.record.funcName,
                "elapsed": None,
                "trace_id": None,
                "span_id": None,
                "parent_id": None,
            }}


class AddSource(JsonModifier):

    def apply(self, context: JsonModifierContext) -> JsonEntry:
        if event := context.event:
            return context.entry | {"source": {
                "func": event.frame.function if event.frame else context.record.funcName,
                "file": trim_path(event.frame.filename) if event.frame else trim_path(context.record.filename),
                "line": event.frame.lineno if event.frame else context.record.lineno,
            }}
        else:
            return context.entry | {"source": {
                "func": context.record.funcName,
                "file": context.record.filename,
                "line": context.record.lineno,
            }}


class AddProperties(JsonModifier):

    def __init__(self, names: Optional[list[str]] = None):
        self.names = names or ["src"]

    def apply(self, context: JsonModifierContext) -> JsonEntry:
        if event := context.event:
            return context.entry | {"properties": event.state}
        else:
            return context.entry | {"properties": {}}


class AddException(JsonModifier):

    def apply(self, context: JsonModifierContext) -> JsonEntry:
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


class AddEnvironmentVariables(JsonModifier):

    def __init__(self, names: list[str]):
        self.names = names

    def apply(self, context: JsonModifierContext) -> JsonEntry:
        env = {k: os.environ.get(k) for k in self.names}
        return context.entry | {"environment": env} if env else context.entry
