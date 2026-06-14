from typing import Any

from wiretap.core.activity import Bulk, Buzz, QuickBulk, QuickBuzz, QuickSnap, Snap, StatusLogPolicy
from wiretap.core.activity_status import Fail, Noop, Okay, Ready, Void
from wiretap.core.annotations import FeedToMessagePart, FeedToStateItem
from wiretap.util.activity_status import ActivityStatus


def begin_buzz(buzz: Buzz, trace_id: Any | None = None, frame_offset: int = 0, with_caller_info: bool = True):
    from wiretap.util.activity_scope import begin_buzz as _begin_buzz

    return _begin_buzz(buzz, trace_id, frame_offset, with_caller_info)


def begin_bulk(bulk: Bulk, trace_id: Any | None = None, frame_offset: int = 0, with_caller_info: bool = True):
    from wiretap.util.activity_scope import begin_bulk as _begin_bulk

    return _begin_bulk(bulk, trace_id, frame_offset, with_caller_info)


def log_snap[S: Snap](snap: S, status: ActivityStatus[S], trace_id: Any | None = None) -> None:
    from wiretap.util.activity_scope import log_snap as _log_snap

    _log_snap(snap, status, trace_id)


__all__ = [
    "begin_buzz",
    "begin_bulk",
    "log_snap",
    "Bulk",
    "Buzz",
    "Snap",
    "QuickBulk",
    "QuickBuzz",
    "QuickSnap",
    "StatusLogPolicy",
    "Okay",
    "Fail",
    "Ready",
    "Void",
    "Noop",
    "FeedToStateItem",
    "FeedToMessagePart",
]
