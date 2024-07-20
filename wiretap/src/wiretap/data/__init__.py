import dataclasses
import inspect
import logging
import uuid
from enum import auto, IntEnum
from typing import Protocol, Optional, Any, Iterator

from _reusable import Elapsed, KebabEnum

WIRETAP_KEY = "_wiretap"


class Procedure(Protocol):
    func: str
    file: str
    line: int
    parent: Optional["Procedure"]
    id: uuid.UUID
    name: str
    data: dict[str, Any] | None
    tags: set[str] | None
    elapsed: Elapsed
    depth: int
    times: int
    trace_count: int

    @property
    def execution(self) -> "Execution":
        pass

    def __iter__(self) -> Iterator["Procedure"]:
        pass


class Execution:

    def __init__(self, procedure: Procedure):
        self.id: uuid.UUID = [x.id for x in procedure][-1]
        self.path: list[str] = [x.name for x in procedure]
        self.elapsed: float = [x.elapsed.current for x in procedure][-1]


@dataclasses.dataclass
class Trace:
    name: str | None
    message: str | None
    data: dict[str, Any]
    tags: set[str]


class TraceLevel(IntEnum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    ERROR = logging.ERROR


class TraceTag(KebabEnum):
    AUTO = auto()
    EVENT = auto()
    PLAIN = auto()
    LOOP = auto()
    UNHANDLED = auto()
    FEATURE = auto()


@dataclasses.dataclass
class Entry:
    procedure: Procedure
    trace: Trace
