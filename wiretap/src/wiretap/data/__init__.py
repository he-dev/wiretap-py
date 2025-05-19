from enum import auto
from typing import Any, Protocol

from tools import KebabEnum


class TraceTag(KebabEnum):
    AUTO = auto()  # Telemetry automatically provided by wiretap.
    PLAIN = auto()  # Telemetry logged with plain logger without wiretap.
    LOOP = auto()


class TagSet:
    def __init__(self, tags: set[Any] | None):
        self.tags = tags or set()

    def __or__(self, other: set[Any] | None) -> "TagSet":
        return TagSet(self.tags | (other or set()))

    def __call__(self):
        return sorted(set(str(x) for x in self.tags))


class LoopStats(Protocol):

    @property
    def count(self) -> int: ...

    def collect(self, elapsed: float, smooth: bool) -> None: ...

    def dump(self) -> dict[str, Any]: ...
