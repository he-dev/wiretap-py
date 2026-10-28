import logging
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from logging import LogRecord
from typing import Any

from wiretap.util.buzz.render_message import render_message

# util: Type alias for convenience.
LogJson = dict[str, Any]


# meta: Using ABC because we're creating objects dynamically.
class BuildJSON(ABC):
    """Allows modifying the structure of the JSON entry."""

    root_keys: tuple[str, ...] = ()

    @abstractmethod
    def __call__(self, record: LogRecord, json: LogJson) -> LogJson: ...


class AddTimestamp(BuildJSON):
    root_keys = ("timestamp",)

    def __init__(self, tz: str = "utc"):
        super().__init__()
        match tz.casefold().strip():
            case "utc":
                self.tz = datetime.now(timezone.utc).tzinfo  # timezone.utc
            case "local" | "lt":
                self.tz = datetime.now(timezone.utc).astimezone().tzinfo
            case _:
                raise ValueError(f"Invalid timezone: {tz}. Only [utc|local] are supported.")

    def __call__(self, record: logging.LogRecord, json: LogJson) -> LogJson:
        return json | {
            "timestamp": datetime.fromtimestamp(record.created, tz=self.tz)
        }


class AddMessage(BuildJSON):
    root_keys = ("message", "logger", "level")

    def __call__(self, record: logging.LogRecord, json: LogJson) -> LogJson:
        return json | {
            "message": render_message(record),
            "logger": record.name,
            "level": record.levelname.lower(),
        }


class AddActivity(BuildJSON):
    root_keys = ("activity",)

    def __call__(self, record: logging.LogRecord, json: LogJson) -> LogJson:
        if activity := record.__dict__.get("activity", {}):
            return json | {"activity": activity}
        else:
            return json | {
                "activity": {
                    "about": None,
                    "event": None,
                }
            }


class AddSource(BuildJSON):
    root_keys = ("source",)

    def __call__(self, record: logging.LogRecord, json: LogJson) -> LogJson:
        activity = record.__dict__.get("activity", {})
        include_source = (
                (logging.getLogger(record.name).isEnabledFor(logging.DEBUG) and activity.get("event") == "ZERO")
                or record.levelno >= logging.ERROR
        )

        if include_source:
            return json | {"source": {
                "func": record.funcName,
                "file": record.filename,
                "line": record.lineno,
            }}

        return json


class AddContext(BuildJSON):
    def __init__(self, key: str | None = "context"):
        self.key = key
        self.root_keys = (key,) if key is not None else ("context",)

    def __call__(self, record: logging.LogRecord, json: LogJson) -> LogJson:
        context = record.__dict__.get("context")
        if self.key is not None:
            return json | {self.key: context}

        # core: Promote context properties to root if they do not conflict with reserved root keys.
        # core: Contex properties that conflict with reserved root keys stay in context as fallback.
        root_keys = set(json) | {"context", "@errors"}
        json["context"] = {}
        for key, value in (context or {}).items():
            if key in root_keys:
                json["context"][key] = value
            else:
                json[key] = value

        # core: Report one collision error regardless of how many keys conflict.
        if json["context"]:
            json["@errors"] = [*(json.get("@errors") or []), "CONTEXT_ROOT_KEY_COLLISION"]
        return json


class AddTrace(BuildJSON):
    root_keys = ("trace",)

    def __call__(self, record: logging.LogRecord, json: LogJson) -> LogJson:
        return json | {
            "trace": record.__dict__.get("trace", None)
        }


class AddException(BuildJSON):
    root_keys = ("exception",)

    def __call__(self, record: logging.LogRecord, json: LogJson) -> LogJson:
        if record.exc_info and all(record.exc_info):
            exc_cls, exc, exc_tb = record.exc_info
            # note: format_exception returns a list of lines. Join it a single sing or otherwise an array will be logged.
            return json | {"exception": {
                "message": str(exc),
                "type": exc_cls.__name__,  # type: ignore
                "stack_trace": "".join(traceback.format_exception(exc_cls, exc, exc_tb))
            }}

        return json


# note: Experimental.
class Redact(BuildJSON):
    """Replaces values at dotted paths; '*' matches one dictionary key or list index."""

    def __init__(self, paths: list[str], replacement: str = "[REDACTED]"):
        self.paths = tuple(tuple(path.split(".")) for path in paths)
        self.replacement = replacement

    def __call__(self, record: logging.LogRecord, json: LogJson) -> LogJson:
        return {key: self._redact(value, (key,)) for key, value in json.items()}

    def _redact(self, value: Any, path: tuple[str, ...]) -> Any:
        if self._matches(path):
            return self.replacement

        # core: Rebuild containers so redaction cannot change values shared with the log record.
        if isinstance(value, dict):
            return {key: self._redact(child, (*path, key)) for key, child in value.items()}
        if isinstance(value, list):
            return [self._redact(child, (*path, str(index))) for index, child in enumerate(value)]
        return value

    def _matches(self, path: tuple[str, ...]) -> bool:
        for pattern in self.paths:
            if len(pattern) != len(path):
                continue

            matches = True
            for expected, actual in zip(pattern, path):
                if expected != "*" and expected != actual:
                    matches = False
                    break

            if matches:
                return True

        return False


# note: Experimental
class RemoveNone(BuildJSON):
    """Removes root-level fields containing None, leaving nested values untouched."""

    def __call__(self, record: logging.LogRecord, json: LogJson) -> LogJson:
        return {key: value for key, value in json.items() if value is not None}
