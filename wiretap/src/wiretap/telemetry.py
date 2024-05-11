import contextlib
import inspect
import sys
import uuid
from typing import Any, Iterator, Type, Optional

from .context import current_activity
from .activity import Activity


@contextlib.contextmanager
def begin_activity(
        name: str | None = None,
        message: str | None = None,
        snapshot: dict[str, Any] | None = None,
        tags: set[str] | None = None
) -> Iterator[Activity]:
    from _reusable import Node
    stack = inspect.stack(2)
    frame = stack[2]
    scope = Activity(name=name or frame.function, frame=frame)
    parent = current_activity.get()
    # The UUID needs to be created here,
    # because for some stupid pythonic reason creating a new Node isn't enough.
    token = current_activity.set(Node(value=scope, parent=parent, id=uuid.uuid4()))
    try:
        scope.log_trace(
            name="begin",
            message=message,
            snapshot=snapshot,
            tags=(tags or set()) | {"auto"}
        )
        yield scope
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if exc_type is not None:
            scope.log_error(message=f"Unhandled <{exc_type.__name__}> has occurred: <{str(exc_value) or 'N/A'}>", tags={"auto", "unhandled"})
        raise
    finally:
        scope.log_end(tags={"auto"})
        current_activity.reset(token)
