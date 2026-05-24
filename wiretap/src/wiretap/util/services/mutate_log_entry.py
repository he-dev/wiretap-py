import dataclasses
import logging
import os
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

from wiretap.util.activity_scope import ActivityScope
from wiretap.util.span import SpanEvent, Span
from wiretap.meta import trim_path

# util: Type alias for convenience
JSONEntry = dict[str, Any]


@dataclasses.dataclass
class ComposeJSONContext:
    record: logging.LogRecord

    @property
    def scope(self) -> ActivityScope[Any] | None:
        return ActivityScope.current()

        if event := SpanEvent.extract_from(self.record):
            return event

        if span := Span.current():
            return SpanEvent(span)

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
        if event := context.scope:

            return context.entry | {
                "operation": event.operation,
                "status": event.status,
                "trace_id": event.trace_id,
                "span_id": event.span_id,
                "parent_id": event.parent_id,
            } | event.stopwatch.to_dict()
        else:
            return context.entry | {
                "operation": context.record.funcName,
                "status": None,
                "trace_id": None,
                "span_id": None,
                "parent_id": None,
                "start_at": None,
                "end_at": None,
            }


class AddSource(ComposeJSON):

    def __call__(self, context: ComposeJSONContext) -> JSONEntry:
        if scope := context.scope:
            return context.entry | {"source": {
                "func": scope.frame.function if scope.frame else context.record.funcName,
                "file": trim_path(scope.frame.filename) if scope.frame else trim_path(context.record.filename),
                "line": scope.frame.lineno if scope.frame else context.record.lineno,
            }}
        else:
            return context.entry | {"source": {
                "func": context.record.funcName,
                "file": context.record.filename,
                "line": context.record.lineno,
            }}


class AddProperties(ComposeJSON):

    def __init__(self, names: Optional[list[str]] = None):
        self.names = names or ["src"]

    def __call__(self, context: ComposeJSONContext) -> JSONEntry:
        if scope := context.scope:
            return context.entry | {"properties": scope.state_items}
        else:
            return context.entry | {"properties": {}}


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
