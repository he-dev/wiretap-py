import contextlib
import dataclasses
import inspect
import logging
import secrets
from contextvars import ContextVar  # noqa: built-in module
from functools import reduce
from inspect import FrameInfo
from typing import Optional, Any, Iterator, TypeVar

from wiretap.util import Elapsed

T = TypeVar("T", bound="ActivityScope")


class ActivityScope:
    """
    This class represents a single telemetry scope.
    """

    current: ContextVar[Optional["ActivityScope"]] = ContextVar("current_activity", default=None)

    def __init__(
            self,
            trace_id: Any | None,
            parent_id: Any | None,
            name: str | None,
            state: dict[str, Any] | None,
            frame: FrameInfo,
            parent: Optional["ActivityScope"],
            **kwargs,
    ):
        self.trace_id: str = trace_id or (parent.trace_id if parent else secrets.token_hex(16))
        self.span_id: str = secrets.token_hex(8)
        self.parent_id: str | None = parent_id or (parent.span_id if parent else None)
        self.name: str = name or frame.function
        self.state: dict = (state or {}) | kwargs
        self.frame: FrameInfo = frame
        self.parent: Optional["ActivityScope"] = parent
        self.elapsed: Elapsed = Elapsed()
        self.logger: logging.Logger = logging.getLogger(name)

    def __iter__(self) -> Iterator["ActivityScope"]:
        current: Optional["ActivityScope"] = self
        while current:
            yield current
            current = current.parent

    @staticmethod
    def log_event(
            message: str | None = None,
            level: int = logging.INFO,
            state: dict | None = None,
            frame_at: int | None = None,
            **kwargs
    ) -> None:
        """Logs scrap trace at the info level."""

        if scope := ActivityScope.peek():
            stack = inspect.stack(2)
            frame = stack[frame_at] if frame_at else scope.frame

            scope.logger.log(
                level=level,
                msg=message,
                exc_info=level >= logging.ERROR,
                extra={
                    ActivityEvent.KEY: ActivityEvent(scope=scope, frame=frame, state=state, **kwargs)
                }
            )
        else:
            raise RuntimeError("No activity in scope.")

    @classmethod
    @contextlib.contextmanager
    def push(
            cls: type[T],
            name: str | None,
            trace_id: Any | None,
            parent_id: Any | None,
            state: dict[str, Any] | None,
            frame: FrameInfo,
            **kwargs,
    ) -> Iterator[T]:
        """
        Pushes a new telemetry scope onto the stack.

        Parameters:
        :param name: Name of the scope, derived from the calling frame if not provided.
        :param state: Extra data to attach to the scope.
        :param frame: Frame information about the scope’s context.

        :returns: The newly created scope.
        """

        if frame is None:
            raise ValueError("FrameInfo must not be None.")

        parent = cls.peek()
        scope = cls(name=name, trace_id=trace_id, parent_id=parent_id, state=state, frame=frame, parent=parent, **kwargs)
        token = cls.current.set(scope)
        try:
            yield scope
        finally:
            cls.current.reset(token)

    @classmethod
    def peek(cls) -> Optional["ActivityScope"]:
        # core: Gets current activity from the stack.
        return cls.current.get()


@dataclasses.dataclass
class ActivityEvent:
    KEY = "_activity_event"

    def __init__(self, scope: ActivityScope, frame: FrameInfo | None = None, state: dict[str, Any] | None = None, **kwargs):
        self.scope = scope.name
        self.frame = frame
        self.trace_id = scope.trace_id
        self.span_id = scope.span_id
        self.parent_id = scope.parent_id
        self.elapsed = scope.elapsed.value
        self.state = reduce(lambda c, n: (n.state or {}) | c, scope, (state or {}) | kwargs)
