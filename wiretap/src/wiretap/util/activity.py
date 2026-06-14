from dataclasses import dataclass, field
from enum import Flag, auto
from typing import ClassVar


@dataclass  # (frozen=True)
class Activity:
    tags: ClassVar[list[object] | None] = None

    @property
    def name(self) -> str:
        return type(self).__qualname__


class StatusLogPolicy(Flag):
    NONE = 0
    FIRST = auto()
    LAST = auto()
    BOTH = FIRST | LAST


@dataclass
class Buzz(Activity):
    pass


@dataclass
class Bulk[I: Buzz](Buzz):
    _item_status_log_policy: ClassVar[StatusLogPolicy] = StatusLogPolicy.BOTH
    _item_status_log_policy_override: StatusLogPolicy | None = field(default=None, init=False, repr=False)

    @property
    def item_status_log_policy(self) -> StatusLogPolicy:
        if self._item_status_log_policy_override is not None:
            return self._item_status_log_policy_override

        return type(self)._item_status_log_policy

    @item_status_log_policy.setter
    def item_status_log_policy(self, value: StatusLogPolicy) -> None:
        self._item_status_log_policy_override = value


@dataclass
class Snap(Activity):
    pass


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
