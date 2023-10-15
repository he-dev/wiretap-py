import dataclasses
import uuid
from contextvars import ContextVar
from typing import Protocol, Optional, Any

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {activity} | {trace} | {elapsed:.3f}s | {message} | {details} | node://{parent_id}/{unique_id} | {attachment}"


class LoggerMeta(Protocol):
    """Represents the properties of the default logger."""

    id: uuid.UUID
    subject: str
    activity: str

    @property
    def elapsed(self) -> float: return ...

    depth: int
    parent: "LoggerMeta"


class TracerMeta(Protocol):
    """Represents the properties of the trace logger."""

    logger: LoggerMeta
    traces: set[str]


current_tracer: ContextVar[Optional[TracerMeta]] = ContextVar("current_tracer", default=None)


@dataclasses.dataclass
class ContextExtra:
    parent_id: uuid.UUID | None
    unique_id: uuid.UUID | None
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
    unique_id: uuid.UUID | None
    subject: str
    activity: str
    trace: str
    elapsed: float
    details: dict[str, Any] | None
    attachment: str | None


class InitialExtra(Protocol):
    inputs: dict[str, Any] | None
    inputs_spec: dict[str, str | None] | None


class FinalExtra(Protocol):
    output: Any | None
    output_spec: str | None
