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
    correlation: "Correlation"
    depth: int
    times: int
    trace_count: int

    def __iter__(self) -> Iterator["Procedure"]:
        pass


@dataclasses.dataclass
class Correlation:
    id: Any
    type: str = "default"


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
