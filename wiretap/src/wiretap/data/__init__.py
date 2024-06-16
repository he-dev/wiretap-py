import dataclasses
import inspect
import uuid
from enum import Enum
from typing import Protocol, Optional, Any, Iterator

from _reusable import Elapsed

WIRETAP_KEY = "_wiretap"


class Activity(Protocol):
    parent: Optional["Activity"]
    id: uuid.UUID
    name: str
    frame: inspect.FrameInfo
    snapshot = Optional[dict[str, Any]]
    tags: Optional[set[str | Enum]]
    elapsed: Elapsed

    @property
    def depth(self) -> int:
        pass

    def __iter__(self) -> Iterator["Activity"]:
        pass


@dataclasses.dataclass
class Trace:
    name: str
    message: str


@dataclasses.dataclass
class Entry:
    activity: Activity
    trace: Trace
    note: dict[str, Any]
    tags: set[str]

    @property
    def tags_sorted(self) -> list[str]:
        return sorted(self.tags, key=lambda x: str(x) if isinstance(x, Enum) else x)
