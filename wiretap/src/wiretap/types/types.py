from logging import DEBUG
import dataclasses
import uuid
from datetime import datetime
from types import TracebackType
from typing import Protocol, Optional, Any, TypeAlias, Type, Callable

ExcInfo: TypeAlias = tuple[Type[BaseException], BaseException, TracebackType]


class Logger(Protocol):
    id: uuid.UUID
    subject: str
    activity: str
    depth: int
    parent: Optional["Logger"]

    @property
    def elapsed(self) -> float: return ...  # noqa

    def log_trace(
            self,
            name: str,
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None,
            level: int = DEBUG,
            exc_info: Optional[ExcInfo | bool] = None
    ): ...


class Tracer(Protocol):
    default: Logger
    sources: set[str]


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


class InitialExtra(Protocol):
    inputs: dict[str, Any] | None
    inputs_spec: dict[str, str | Callable | None] | None


class FinalExtra(Protocol):
    output: Any | None
    output_spec: str | Callable | None
