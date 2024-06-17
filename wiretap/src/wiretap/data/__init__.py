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
    type: str
    name: str
    frame: inspect.FrameInfo
    extra: dict[str, Any] | None
    tags: set[str] | None
    elapsed: Elapsed
    correlation: "Correlation"

    @property
    def depth(self) -> int:
        pass

    def __iter__(self) -> Iterator["Activity"]:
        pass


@dataclasses.dataclass
class Correlation:
    id: Any
    type: str = "default"


@dataclasses.dataclass
class Trace:
    type: str
    name: str | None
    message: str | None


@dataclasses.dataclass
class Entry:
    activity: Activity
    trace: Trace
    extra: dict[str, Any]
    tags: set[str]

    @property
    def tags_sorted(self) -> list[str]:
        return sorted(self.tags, key=lambda x: str(x) if isinstance(x, Enum) else x)
