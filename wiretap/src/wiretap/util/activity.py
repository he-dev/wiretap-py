from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import ClassVar


@dataclass  # (frozen=True)
class Activity:
    tags: ClassVar[list[object] | None] = None

    @property
    def name(self) -> str:
        return type(self).__qualname__


@dataclass  # (frozen=True)
class ActivityStatus[A: Activity]:
    # core: The phantom A binds a status to one activity type.
    level: ClassVar[int] = logging.INFO

    @property
    def code(self) -> str:
        # meta: Gets the status code from the concrete subclass but nearest to ActivityStatus.
        for cls in type(self).__mro__:
            # note: Flags are derived directly from ActivityStatus.
            if cls.__base__ is ActivityStatus:
                return cls.__name__
        raise TypeError(f"Activity status code not found because {type(self).__qualname__} does not inherit : must inherit from {ActivityStatus.__qualname__}.")


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
