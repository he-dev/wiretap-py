from abc import ABC, abstractmethod
from typing import Any


# note: Must be an ABC because issubclass does not work with protocols and the encoder needs to check it.
class LoopStats(ABC):

    @property
    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def collect(self, elapsed: float, smooth: bool) -> None: ...

    @abstractmethod
    def dump(self) -> dict[str, Any]: ...
