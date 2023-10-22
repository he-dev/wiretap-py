import dataclasses
import uuid
from contextvars import ContextVar
from datetime import datetime
from logging import DEBUG
from types import TracebackType
from typing import Protocol, Optional, Any, TypeAlias, Type

from ..parts import Elapsed, Node

ExcInfo: TypeAlias = tuple[Type[BaseException], BaseException, TracebackType]


class Logger(Protocol):
    subject: str
    activity: str
    elapsed: Elapsed

    def log_trace(
            self,
            name: str,
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None,
            level: int = DEBUG,
            exc_info: Optional[ExcInfo | bool] = None
    ): ...


current_logger: ContextVar[Optional[Node[Logger]]] = ContextVar("current_logger", default=None)


@dataclasses.dataclass
class ContextExtra:
    parent_id: uuid.UUID | None
    unique_id: uuid.UUID
    subject: str
    activity: str


@dataclasses.dataclass
class TraceExtra:
    trace: str
    elapsed: float
    details: dict[str, Any] | None
    attachment: str | None


class DefaultExtra(Protocol):
    parent_id: uuid.UUID | None
    unique_id: uuid.UUID
    timestamp: datetime
    subject: str
    activity: str
    trace: str
    elapsed: float
    details: dict[str, Any] | None
    attachment: str | None
