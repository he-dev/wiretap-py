import logging
from dataclasses import dataclass
from typing import Annotated, ClassVar

from wiretap.core.annotations import FeedToMessagePart, FeedToStateItem
from wiretap.util.activity import Activity
from wiretap.util.activity_feed import PushItem
from wiretap.util.activity_status import ActivityStatus


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
