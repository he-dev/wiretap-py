from abc import ABC, abstractmethod
from typing import Any


# note: Must be an ABC because issubclass does not work with protocols and some encoders need to check it.
class LoopStats(ABC):
    count: int
    elapsed: float

    @abstractmethod
    def count_item(self, elapsed: float) -> None: ...


class Serializable(ABC):

    @abstractmethod
    def to_dict(self) -> dict[str, Any]: ...
