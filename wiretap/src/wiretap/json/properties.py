import functools
import logging
import os
import traceback
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol, Any

from _reusable import nth_or_default, Node
from wiretap import current_procedure
from wiretap.data import WIRETAP_KEY, Procedure, Entry


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


class ExecutionProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            entry: Entry = record.__dict__[WIRETAP_KEY]
            procedure = entry.procedure
            return {
                "execution": {
                    "path": [x.name for x in procedure],
                    "elapsed": [x.elapsed.current for x in procedure][-1],
                }
            }
        else:
            node: Node | None = current_procedure.get()
            if node:
                procedure = node.value
                return {
                    "execution": {
                        "path": [x.name for x in procedure],
                        "elapsed": [x.elapsed.current for x in procedure][-1],
                    }
                }
            else:
                return {
                    "execution": {
                        "path": None,
                        "elapsed": None,
                    }
                }


class ProcedureProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            entry: Entry = record.__dict__[WIRETAP_KEY]
            procedure = entry.procedure
            return {
                "procedure": {
                    "id": procedure.id,
                    "name": procedure.name,
                    "elapsed": procedure.elapsed.current,
                    "depth": procedure.depth,
                    "times": procedure.times,
                }
            }
        else:
            node: Node | None = current_procedure.get()
            if node:
                procedure = node.value
                return {
                    "procedure": {
                        "id": procedure.id,
                        "name": procedure.name,
                        "elapsed": procedure.elapsed.current,
                        "depth": procedure.depth,
                        "times": procedure.times,
                    }
                }
            else:
                return {
                    "procedure": {
                        "id": None,
                        "name": record.funcName,
                        "elapsed": None,
                        "depth": None,
                    }
                }


class CorrelationProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            entry: Entry = record.__dict__[WIRETAP_KEY]
            return {
                "correlation": {
                    # "id": [a.id for a in entry.activity][-1]
                    "id": entry.procedure.correlation.id,
                    "type": entry.procedure.correlation.type,
                }
            }
        else:
            node: Node | None = current_procedure.get()
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
                    "name": entry.trace.name,
                    "message": entry.trace.message,
                    "data": entry.trace.data,
                    "tags": sorted(entry.trace.tags),
                }
            }
        else:
            return {
                "trace": {
                    "name": record.levelname.lower(),
                    "message": record.msg,
                    "data": None,
                    "tags": ["plain"]
                }
            }


class SourceProperty(JSONProperty):

    def emit(self, record: logging.LogRecord) -> dict[str, Any]:
        if WIRETAP_KEY in record.__dict__:
            entry: Entry = record.__dict__[WIRETAP_KEY]
            if entry.procedure.trace_count == 1:
                return {
                    "source": {
                        "func": entry.procedure.frame.function,
                        "file": entry.procedure.frame.filename,
                        "line": entry.procedure.frame.lineno,
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
