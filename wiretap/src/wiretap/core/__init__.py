import pathlib
from typing import Any

import yaml

from .activity import Buzz, PrototypeBuzz, PrototypeSnap, Snap
from .activity_status import Fail, Noop, Okay, Ready, Void
from .annotations import FeedToMessagePart, FeedToStateItem


def begin_buzz(activity: Buzz, trace_id: Any | None = None, frame_offset: int = 0, with_caller_info: bool = True):
    from wiretap.util.activity_scope import begin_buzz as _begin_buzz

    return _begin_buzz(activity, trace_id, frame_offset, with_caller_info)


def log_status(snap: Snap, status, trace_id: Any | None = None) -> None:
    from wiretap.util.activity_scope import log_status as _log_status

    _log_status(snap, status, trace_id)


__all__ = [
    "begin_buzz",
    "log_status",
    "Buzz",
    "Snap",
    "PrototypeBuzz",
    "PrototypeSnap",
    "Okay",
    "Fail",
    "Ready",
    "Void",
    "Noop",
    "FeedToStateItem",
    "FeedToMessagePart",
]
