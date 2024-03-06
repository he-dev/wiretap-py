import contextlib
import inspect
import logging
import sys
import uuid
from typing import Any

from .context import current_activity
from .tools import Node
from .tracing import Activity


@contextlib.contextmanager
def begin_activity(
        name: str | None = None,
        message: str | None = None,
        snapshot: dict[str, Any] | None = None
) -> None:
    stack = inspect.stack(2)
    frame = stack[2]
    activity = Activity(
        name=name or frame[3],
        frame=frame
    )
    parent = current_activity.get()
    token = current_activity.set(Node(value=activity, parent=parent, id=uuid.uuid4()))
    try:
        log(
            event="started",
            message=message,
            snapshot=snapshot
        )
        yield None
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        log_error(message=f"Unhandled <{exc_type.__name__}> has occurred: <{str(exc_value) or 'N/A'}>")
        raise
    finally:
        log_completed()
        current_activity.reset(token)


def log(event: str, message: str, snapshot: dict, exc_info: bool = False) -> None:
    activity: Activity = current_activity.get().value
    if not activity:
        raise Exception("There is no activity in the current scope.")

    activity.logger.log(
        level=logging.INFO,
        msg=message,
        exc_info=exc_info,
        extra=dict(
            event=event,
            snapshot=snapshot or {}
        )
    )


def _current_activity() -> Activity:
    activity: Activity = current_activity.get().value
    if not activity:
        raise Exception("There is no activity in the current scope.")
    return activity


def log_info(message: str | None = None, snapshot: dict | None = None) -> None:
    activity = _current_activity()
    if not activity.is_open.state:
        raise Exception(f"The current '{activity.name}' activity is no longer open.")
    log("info", message, snapshot)


def log_completed(message: str | None = None, snapshot: dict | None = None) -> None:
    if _current_activity().is_open:
        log("completed", message, snapshot)


def log_cancelled(message: str | None = None, snapshot: dict | None = None) -> None:
    if _current_activity().is_open:
        log("cancelled", message, snapshot)


def log_error(message: str | None = None, snapshot: dict | None = None) -> None:
    if _current_activity().is_open:
        log("error", message, snapshot, exc_info=True)


"""

- activity
    - parent_id - auto
    - unique_id - auto
    - timestamp - auto
    - activity - auto

- trace
    - trace
        - name: begin|state|end
        - type: auto|user
        - reason: completed|cancelled|error
    - elapsed - auto
    - message - user
    - snapshot - user
        - file
            - name
            - line
    - exception - auto

"""
