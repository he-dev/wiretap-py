import asyncio
import contextlib
import dataclasses
import enum
import functools
import inspect
import json
import logging
import re
import sys
import uuid
from collections.abc import Generator
from contextvars import ContextVar
from datetime import datetime, date, timezone
from timeit import default_timer as timer
from types import TracebackType
from typing import Dict, Callable, Any, Protocol, Optional, Iterator, TypeVar, TypeAlias, Generic, ContextManager, Type
from ..data import current_logger, LogRecordExtra


class ConstField(logging.Filter):
    def __init__(self, name: str, value: Any):
        self.value = value
        super().__init__(name)

    def filter(self, record: logging.LogRecord) -> int:
        setattr(record, self.name, self.value)
        return 1


class TimestampField(logging.Filter):
    def __init__(self, tz: timezone = timezone.utc):
        super().__init__("timestamp")
        self.tz = tz

    def filter(self, record: logging.LogRecord) -> int:
        setattr(record, self.name, datetime.fromtimestamp(record.created, tz=self.tz))
        return 1


class LevelField(logging.Filter):
    def __init__(self):
        super().__init__("level")

    def filter(self, record: logging.LogRecord) -> int:
        setattr(record, self.name, record.levelname.lower())
        return 1


class IndentField(logging.Filter):
    def __init__(self, char: str = "."):
        super().__init__("indent")
        self.char = char

    def filter(self, record: logging.LogRecord) -> int:
        current = current_logger.get()
        if current:
            setattr(record, self.name, self.char * (current.depth or 1))
        return 1


class SerializeDetails(Protocol):
    def __call__(self, value: Optional[Dict[str, Any]]) -> str | None: ...


class _JsonDateTimeEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, (date, datetime)):
            return o.isoformat()


class SerializeDetailsToJson(SerializeDetails):
    def __call__(self, value: Optional[Dict[str, Any]]) -> str | None:
        return json.dumps(value, sort_keys=True, allow_nan=False, cls=_JsonDateTimeEncoder) if value else None


class SerializeDetailsField(logging.Filter):
    def __init__(self, serialize: SerializeDetails = SerializeDetailsToJson()):
        super().__init__("serialize_details")
        self.serialize = serialize

    def filter(self, record: logging.LogRecord) -> int:
        if hasattr(record, "details") and isinstance(record.details, dict):
            record.details = self.serialize(record.details)
        return 1


class ExtraFields(logging.Filter):
    def __init__(self):
        super().__init__("extra")

    def filter(self, record: logging.LogRecord) -> int:
        if not hasattr(record, "trace"):
            current = current_logger.get()
            extra = LogRecordExtra(
                parent_id=current.parent.id if current and current.parent else None,
                unique_id=current.id if current else None,
                subject=current.subject if current else record.module,
                activity=current.activity if current else record.funcName,
                trace="info",
                elapsed=current.elapsed if current else 0,
                details={},
                attachment=None
            )

            for k, v in vars(extra).items():
                record.__dict__[k] = v

        return 1
