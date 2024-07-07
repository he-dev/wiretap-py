import dataclasses
import inspect
import uuid
from typing import Protocol, Optional, Any, Iterator

from _reusable import Elapsed

WIRETAP_KEY = "_wiretap"


class Procedure(Protocol):
    parent: Optional["Procedure"]
    id: uuid.UUID
    name: str | None
    frame: inspect.FrameInfo
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


@dataclasses.dataclass
class Entry:
    procedure: Procedure
    trace: Trace
