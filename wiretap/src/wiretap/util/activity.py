from dataclasses import dataclass
from typing import ClassVar


@dataclass  # (frozen=True)
class Activity:
    tags: ClassVar[list[object] | None] = None

    @property
    def name(self) -> str:
        return type(self).__qualname__


class LastStatusCount:
    def __init__(self) -> None:
        self._value = 0

    def increment(self) -> None:
        self._value += 1

    @property
    def value(self) -> int:
        return self._value

    @property
    def overflows(self) -> bool:
        return self._value > 1

    @property
    def is_zero(self) -> bool:
        return self._value == 0
