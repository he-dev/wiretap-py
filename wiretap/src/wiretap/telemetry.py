import contextlib
import inspect
import sys
import uuid
from pathlib import Path
from typing import Any

from .context import current_activity
from .tools import Node
from .tracing import Activity, Reason


@contextlib.contextmanager
def begin_activity(
        name: str | None = None,
        message: str | None = None,
        snapshot: dict[str, Any] | None = None
) -> None:
    stack = inspect.stack(2)
    frame = stack[2]
    activity = Activity(name=name or frame[3])
    parent = current_activity.get()
    token = current_activity.set(Node(value=activity, parent=parent, id=uuid.uuid4()))
    try:
        activity.log(
            trace="begin",
            message=message,
            snapshot=(snapshot or {}) | dict(file=dict(name=Path(frame.filename).name, line=frame.lineno))
        )
        yield None
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        end_activity(
            message=f"Unhandled <{exc_type.__name__}> has occurred: <{str(exc_value) or 'N/A'}>",
            reason=Reason.ERROR
        )
        raise
    finally:
        end_activity()
        current_activity.reset(token)


def trace_state(message: str | None = None, snapshot: dict | None = None) -> None:
    activity: Activity = current_activity.get().value
    if not activity:
        raise Exception("There is no activity in the current scope.")
    if not activity.is_open.state:
        raise Exception(f"The current '{activity.name}' activity is no longer open.")
    activity.log("state", message, snapshot)


def end_activity(message: str | None = None, snapshot: dict[str, Any] | None = None, reason: Reason = Reason.COMPLETED, exception: Exception | None = None) -> None:
    activity: Activity = current_activity.get().value
    if not activity:
        raise Exception("There is no activity in the current scope.")
    if not activity.is_open:
        return
    activity.log("end", message, (snapshot or {}) | dict(reason=reason.value), exc_info=reason == Reason.ERROR)


"""

- activity
    - parent_id - auto
    - unique_id - auto
    - timestamp - auto
    - activity - auto

- trace
    - trace - auto
    - elapsed - auto
    - message - user
    - snapshot - user
        - file
            - name
            - line
    - exception - auto

"""
