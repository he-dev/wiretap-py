import logging
import os
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from logging import LogRecord
from typing import Any, Optional

from wiretap.meta import FormatData

# util: Type alias for convenience.
LogJson = dict[str, Any]


# meta: Using ABC because we're creating objects dynamically.
class BuildJSON(ABC):
    """Allows modifying the structure of the JSON entry."""

    @abstractmethod
    def __call__(self, record: LogRecord, json: LogJson) -> LogJson: ...


class AddTimestamp(BuildJSON):
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

    def __call__(self, record: logging.LogRecord, json: LogJson) -> LogJson:
        return json | {
            "message": None if record.msg is None else record.getMessage().format_map(FormatData(record.__dict__)),
            "logger": record.name,
            "level": record.levelname.lower(),
        }


class AddActivity(BuildJSON):

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


class AddStory(BuildJSON):

    def __call__(self, record: logging.LogRecord, json: LogJson) -> LogJson:
        story = record.__dict__.get("context", {}).pop("story", None)
        if story:
            return json | {
                "story": story
            }

        return json


class AddContext(BuildJSON):

    def __init__(self, names: Optional[list[str]] = None):
        self.names = names or ["src"]

    def __call__(self, record: logging.LogRecord, json: LogJson) -> LogJson:
        return json | {
            "context": record.__dict__.get("context", None)
        }


class AddException(BuildJSON):

    def __call__(self, record: logging.LogRecord, json: LogJson) -> LogJson:
        if record.exc_info and all(record.exc_info):
            exc_cls, exc, exc_tb = record.exc_info
            # note: format_exception returns a list of lines. Join it a single sing or otherwise an array will be logged.
            # entry["trace"]["event"] = exc_cls.__name__
            return json | {"exception": {
                "message": str(exc),
                "type": exc_cls.__name__,  # type: ignore
                "stack_trace": "".join(traceback.format_exception(exc_cls, exc, exc_tb))
            }}

        return json


class AddEnvironmentVariables(BuildJSON):

    def __init__(self, names: list[str]):
        self.names = names

    def __call__(self, record: logging.LogRecord, json: LogJson) -> LogJson:
        env = {k: os.environ.get(k) for k in self.names}
        return json | {"environment": env} if env else json
