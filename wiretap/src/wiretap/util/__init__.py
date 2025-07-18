from enum import auto
from typing import Any, Protocol

from util import KebabEnum


class TraceTag(KebabEnum):
    """ Defines generic and frequently used tags. """
    AUTO = auto()  # Telemetry automatically provided by wiretap.
    PLAIN = auto()  # Telemetry logged with plain logger without "wiretap".
    LOOP = auto()


class TagSet:
    # !! I do not want to repeat tag sorting and stringing everywhere.

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