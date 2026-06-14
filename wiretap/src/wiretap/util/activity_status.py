import logging
from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from wiretap.util.annotations import FeedToMessagePart, FeedToStateItem
from wiretap.util.activity import Activity
from wiretap.util.activity_feed import PushItem


@dataclass
class ActivityStatus[A: Activity]:
    # core: The phantom A binds a status to one activity type.
    level: ClassVar[int] = logging.INFO
    role: ClassVar[str] = "none"

    @property
    def code(self) -> str:
        # meta: Gets the status code from the concrete subclass but nearest to ActivityStatus.
        for cls in type(self).__mro__:
            # note: Flags are derived directly from ActivityStatus.
            if cls.__base__ is ActivityStatus:
                return cls.__name__
        raise TypeError(f"Activity status code not found because {type(self).__qualname__} does not inherit : must inherit from {ActivityStatus.__qualname__}.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.lower(),
            "role": self.role,
        }


# core: The first status emitted by a buzz when its scope is entered.
@dataclass  # (frozen=True)
class Ready[A: Activity](ActivityStatus[A]):
    level: ClassVar[int] = logging.INFO
    role: ClassVar[str] = "first"


# core: everything went according to plan.
@dataclass  # (frozen=True)
class Okay[A: Activity](ActivityStatus[A]):
    level: ClassVar[int] = logging.INFO
    role: ClassVar[str] = "last"


# core: an error occurred.
@dataclass  # (frozen=True)
class Fail[A: Activity](ActivityStatus[A]):
    level: ClassVar[int] = logging.ERROR
    role: ClassVar[str] = "last"
    exception: Exception | None

    def message_parts(self, push: PushItem) -> None:
        if self.exception is not None:
            push("Exception", str(self.exception))


@dataclass  # (frozen=True)
class Void[A: Activity](ActivityStatus[A]):
    level: ClassVar[int] = logging.WARNING
    role: ClassVar[str] = "last"
    reason: Annotated[str, FeedToStateItem(), FeedToMessagePart()]


@dataclass  # (frozen=True)
class Noop[A: Activity](ActivityStatus[A]):
    level: ClassVar[int] = logging.INFO
    role: ClassVar[str] = "last"
