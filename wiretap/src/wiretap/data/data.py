import logging
import dataclasses
import uuid
from contextvars import ContextVar
from types import TracebackType
from typing import Protocol, Optional, Any, TypeAlias, Type, Callable

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {activity} | {trace} | {elapsed:.3f}s | {message} | {details} | node://{parent_id}/{unique_id} | {attachment}"

ExcInfo: TypeAlias = tuple[Type[BaseException], BaseException, TracebackType]


class Logger(Protocol):
    """Represents the default logger."""

    id: uuid.UUID
    subject: str
    activity: str

    @property
    def elapsed(self) -> float: return ...  # noqa

    depth: int
    parent: Optional["Logger"]

    def log_trace(
            self,
            name: str,
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None,
            level: int = logging.DEBUG,
            exc_info: Optional[ExcInfo | bool] = None,
            extra: Optional[dict[str, Any]] = None
    ): ...


class Tracer(Protocol):
    """Represents the properties of the trace logger."""

    default: Logger
    traces: set[str]


current_tracer: ContextVar[Optional[Tracer]] = ContextVar("current_tracer", default=None)


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
