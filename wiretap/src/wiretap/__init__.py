import contextlib
import inspect
import sys
from enum import Enum
from typing import Any, Iterator, Callable, Type, Tuple

from _reusable import Node
from . import formatters
from . import json
from . import scopes
from . import tag
from .context import current_activity
from .scopes import ActivityScope, LoopScope


def dict_config(data: dict):
    import logging.config
    logging.config.dictConfig(data)


@contextlib.contextmanager
def log_activity(
        name: str | None = None,
        message: str | None = None,
        note: dict[str, Any] | None = None,
        tags: set[str] | None = None,
        **kwargs
) -> Iterator[ActivityScope]:
    """This function logs telemetry for an activity scope. It returns the activity scope that provides additional APIs."""
    tags = (tags or set())  # | {tag.AUTO}
    if name:
        tags.add(tag.VIRTUAL)

    from _reusable import Node
    stack = inspect.stack(2)
    frame = stack[2]
    parent = current_activity.get()
    scope = ActivityScope(
        parent=parent.value if parent else None,
        name=name or frame.function,
        frame=frame,
        note=note,
        tags=tags, **kwargs
    )
    # The UUID needs to be created here,
    # because for some stupid pythonic reason creating a new Node isn't enough.
    token = current_activity.set(Node(value=scope, parent=parent, id=scope.id))
    try:
        scope.log_trace(name="begin", message=message, note=note, **kwargs)
        yield scope
    except Exception:
        exc_cls, exc, exc_tb = sys.exc_info()
        if exc is not None:
            scope.log_error(tags={tag.UNHANDLED})
        raise
    finally:
        scope.log_end()
        current_activity.reset(token)


# def log_error(
#         message: str | None = None,
#         snapshot: dict | None = None,
#         tags: set[str | Enum] | None = None,
#         exc_info: bool = True,
#         **kwargs
# ) -> None:
#     parent = current_activity.get()
#     if parent:
#         parent.value.log_error(message, snapshot, tags, exc_info=exc_info, **kwargs)


def log_resource(
        name: str,
        message: str | None = None,
        note: dict[str, Any] | None = None,
        tags: set[str] | None = None,
        **kwargs
) -> Callable[[], None]:
    """This function logs telemetry for a resource. It returns a function that logs the end of its usage when called."""
    scope = log_activity(name, message, note, tags, **kwargs)
    scope.__enter__()

    def dispose():
        scope.__exit__(None, None, None)

    return dispose


@contextlib.contextmanager
def log_loop(
        message: str | None = None,
        tags: set[str] | None = None,
        activity: ActivityScope | None = None,
        **kwargs,
) -> Iterator[LoopScope]:
    """This function initializes a new scope for loop telemetry."""
    loop = LoopScope()
    try:
        yield loop
    finally:
        if activity is None:
            node: Node | None = current_activity.get()
            if node is None:
                raise ValueError("There is no activity in scope.")
            activity = node.value
        activity.log_trace(
            name="loop",
            message=message,
            note=loop.dump(),
            tags=tags,
            **kwargs
        )


def no_exc_info_if(exception_type: Type[BaseException] | Tuple[Type[BaseException], ...]) -> bool:
    exc_cls, exc, exc_tb = sys.exc_info()
    return not isinstance(exc, exception_type)


def to_tag(value: str | Enum) -> str:
    if isinstance(value, Enum):
        value = str(value)

    return value.replace("_", "-")
