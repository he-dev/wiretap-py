from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Annotated, ClassVar

from wiretap.core.annotations import FeedToMessagePart, FeedToStateItem
from wiretap.util.activity import Activity, ActivityStatus
from wiretap.util.activity_feed import PushMessagePart


# core: everything went according to plan.
@dataclass  # (frozen=True)
class Okay[A: Activity](ActivityStatus[A]):
    level: ClassVar[int] = logging.INFO


# core: an error occurred.
@dataclass  # (frozen=True)
class Fail[A: Activity](ActivityStatus[A]):
    level: ClassVar[int] = logging.ERROR
    exception: Exception | None

    def message_parts(self, push: PushMessagePart) -> None:
        if self.exception is not None:
            push(f"Exception: {str(self.exception)}")


# note: the very first status. Its previous name was "First".
@dataclass  # (frozen=True)
class Zero[A: Activity](ActivityStatus[A]):
    level: ClassVar[int] = logging.DEBUG


@dataclass  # (frozen=True)
class Void[A: Activity](ActivityStatus[A]):
    level: ClassVar[int] = logging.DEBUG
    reason: Annotated[str, FeedToStateItem(), FeedToMessagePart()]


@dataclass  # (frozen=True)
class Noop[A: Activity](ActivityStatus[A]):
    level: ClassVar[int] = logging.DEBUG
