import dataclasses
import uuid
from contextvars import ContextVar
from typing import Protocol, Optional, Any

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {activity} | {trace} | {elapsed:.3f}s | {message} | {details} | node://{parent_id}/{unique_id} | {attachment}"


class LoggerMeta(Protocol):
    id: uuid.UUID
    subject: str
    activity: str
    elapsed: float
    depth: int
    parent: "LoggerMeta"


current_logger: ContextVar[Optional[LoggerMeta]] = ContextVar("current_logger", default=None)


@dataclasses.dataclass
class LogRecordExtra:
    parent_id: uuid.UUID | None
    unique_id: uuid.UUID | None
    subject: str
    activity: str
    trace: str
    elapsed: float
    details: dict[str, Any] | None
    attachment: str | None
