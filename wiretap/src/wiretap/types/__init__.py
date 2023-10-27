import uuid
from datetime import datetime
from types import TracebackType
from typing import Protocol, Any, TypeAlias, Type

ExcInfo: TypeAlias = bool | tuple[Type[BaseException], BaseException, TracebackType | None] | tuple[None, None, None] | BaseException | None


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
