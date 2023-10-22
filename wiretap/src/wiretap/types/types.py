import dataclasses
import uuid
from datetime import datetime
from logging import DEBUG
from types import TracebackType
from typing import Protocol, Optional, Any, TypeAlias, Type, Iterator, TypeVar, Generic

ExcInfo: TypeAlias = tuple[Type[BaseException], BaseException, TracebackType]


class Metric(Protocol):
    def __float__(self): ...


TValue = TypeVar("TValue")


class Node(Generic[TValue]):

    def __init__(self, value: TValue, parent: Optional["Node"]):
        self.value = value
        self.parent = parent
        self.id = uuid.uuid4()

    @property
    def depth(self) -> int:
        return self.parent.depth + 1 if self.parent else 1

    def __iter__(self) -> Iterator["Node"]:
        current = self
        while current:
            yield current
            current = current.parent


class Logger(Protocol):
    subject: str
    activity: str
    elapsed: Metric

    def log_trace(
            self,
            name: str,
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None,
            level: int = DEBUG,
            exc_info: Optional[ExcInfo | bool] = None
    ): ...


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
