import pathlib
from typing import Any

import yaml

from wiretap.core.activity import Buzz, QuickBuzz, QuickSnap, Snap
from wiretap.core.activity_status import Fail, Noop, Okay, Ready, Void
from wiretap.core.annotations import FeedToMessagePart, FeedToStateItem
from wiretap.util.activity_status import ActivityStatus


def begin_buzz(buzz: Buzz, trace_id: Any | None = None, frame_offset: int = 0, with_caller_info: bool = True):
    from wiretap.util.activity_scope import begin_buzz as _begin_buzz

    return _begin_buzz(buzz, trace_id, frame_offset, with_caller_info)


def log_snap[S: Snap](snap: S, status: ActivityStatus[S], trace_id: Any | None = None) -> None:
    from wiretap.util.activity_scope import log_snap as _log_snap

    _log_snap(snap, status, trace_id)


__all__ = [
    "begin_buzz",
    "log_snap",
    "Buzz",
    "Snap",
    "QuickBuzz",
    "QuickSnap",
    "Okay",
    "Fail",
    "Ready",
    "Void",
    "Noop",
    "FeedToStateItem",
    "FeedToMessagePart",
]
