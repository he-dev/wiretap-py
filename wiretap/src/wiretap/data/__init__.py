import dataclasses
import inspect
import logging
import uuid
from enum import auto
from typing import Protocol, Optional, Any, Iterator, Callable, TypeVar

from _reusable import Elapsed, KebabEnum

_T = TypeVar("_T", bound="LoggerNode")


class LoggerNode(Protocol[_T]):
    parent: Optional[_T]
    depth: int

    def __iter__(self) -> Iterator[_T]:
        ...


class LoggerData(Protocol):
    frame: inspect.FrameInfo
    id: uuid.UUID
    name: str
    tags: set[str] | None
    elapsed: Elapsed


class LoggerItem(LoggerNode[_T], LoggerData, Protocol[_T]):
    ...


class LoggerPath:

    def __init__(self, block: LoggerItem, selector: Callable[[LoggerItem], Any]):
        self.names: list[str] = [str(selector(x)) for x in block][::-1]

    def __str__(self) -> str:
        return "/".join(self.names)


@dataclasses.dataclass
class LoggerTrace:
    name: str | None
    message: str | None
    state: dict[str, Any]
    tags: set[str]


class TraceTag(KebabEnum):
    AUTO = auto()
    EVENT = auto()
    PLAIN = auto()
    LOOP = auto()
    UNHANDLED = auto()
    FEATURE = auto()


class LogTrace(Protocol):
    def __call__(
            self,
            name: str | None = None,
            message: str | None = None,
            state: dict | None = None,
            tags: set[Any] | None = None,
            exc_info: bool = False,
            in_progress: bool = True,
            level: int = logging.DEBUG,
            **kwargs: Any
    ) -> None:
        ...
