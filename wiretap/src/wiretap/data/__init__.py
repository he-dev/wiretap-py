import dataclasses
import inspect
import logging
import uuid
from enum import auto, IntEnum
from typing import Protocol, Optional, Any, Iterator, Callable, runtime_checkable

from _reusable import Elapsed, KebabEnum

BLOCK_KEY = "_feed"
TRACE_KEY = "_trace"


class Block(Protocol):
    frame: inspect.FrameInfo
    parent: Optional["Block"]
    id: uuid.UUID
    name: str
    tags: set[str] | None
    elapsed: Elapsed
    depth: int
    trace_count: int

    def __iter__(self) -> Iterator["Block"]:
        pass


class FeedPath:

    def __init__(self, block: Block, selector: Callable[[Block], Any]):
        self.names: list[str] = [str(selector(x)) for x in block][::-1]

    def __str__(self) -> str:
        return "/".join(self.names)


@dataclasses.dataclass
class Trace:
    name: str | None
    message: str | None
    state: dict[str, Any]
    tags: set[str]


class TraceLevel(IntEnum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    ERROR = logging.ERROR
    EXCEPTION = logging.CRITICAL


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
            level: TraceLevel = TraceLevel.DEBUG,
            **kwargs: Any
    ) -> None:
        ...
