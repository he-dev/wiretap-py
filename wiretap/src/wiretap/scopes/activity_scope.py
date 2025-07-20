import contextlib
import dataclasses
import inspect
import logging
import secrets
from contextvars import ContextVar  # noqa: built-in module
from functools import reduce
from inspect import FrameInfo
from typing import Optional, Any, Iterator, TypeVar

from util import Elapsed

T = TypeVar("T", bound="ActivityScope")


class ActivityScope:
    """
    This class represents a single telemetry scope.
    """

    current: ContextVar[Optional["ActivityScope"]] = ContextVar("current_activity", default=None)

    def __init__(
            self,
            trace_id: Any | None,
            span_id: Any | None,
            name: str | None,
            state: dict[str, Any] | None,
            frame: FrameInfo,
            parent: Optional["ActivityScope"],
            **kwargs,
    ):
        self.trace_id = trace_id or (parent.trace_id if parent else secrets.token_hex(16))
        self.span_id = span_id or secrets.token_hex(8)
        self.parent_id = parent.span_id if parent else None
        self.name = name or frame.function
        self.state = (state or {}) | kwargs
        self.local = {}
        self.frame = frame
        self.parent = parent
        self.stopped = False

        self.elapsed = Elapsed()
        self.logger: logging.Logger = logging.getLogger(name)

    def __iter__(self) -> Iterator["ActivityScope"]:
        current: Optional["ActivityScope"] = self
        while current:
            yield current
            current = current.parent

    def stop(self) -> None:
        self.stopped = True

    def log_event(
            self,
            message: str | None = None,
            level: int = logging.INFO,
            state: dict | None = None,
            frame: FrameInfo | None = None,
            frame_offset: int = 1,
            **kwargs
    ) -> "ActivityScope":
        """Logs scrap trace at the info level."""

        stack = inspect.stack(2)
        frame = stack[frame_offset] if frame is None else frame

        if not self.stopped:
            self.logger.log(
                level=level,
                msg=message,
                exc_info=level >= logging.ERROR,
                extra=ActivityEvent(
                    scope=self.name,
                    frame=frame or self.frame,
                    trace_id=self.trace_id,
                    span_id=self.span_id,
                    parent_id=self.parent_id,
                    elapsed=self.elapsed.current,
                    # core: Merge states while the current one take precedence.
                    state=reduce(lambda c, n: (n.state or {}) | c, self, (state or {}) | kwargs | self.state)
                ).to_dict()
            )

        return self

    @classmethod
    @contextlib.contextmanager
    def push(
            cls: type[T],
            name: str | None,
            trace_id: Any | None,
            span_id: Any | None,
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
        scope = cls(name=name, trace_id=trace_id, span_id=span_id, state=state, frame=frame, parent=parent, **kwargs)
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
    scope: str
    frame: FrameInfo
    trace_id: str
    span_id: str
    parent_id: str | None
    elapsed: float
    state: dict[str, Any]

    KEY = "_wiretap"

    def to_dict(self) -> dict[str, Any]:
        return {ActivityEvent.KEY: self}

    @classmethod
    def extract_or_default(cls, record: logging.LogRecord) -> Optional["ActivityEvent"]:
        # core: Try to get activity-event from the record.
        if item := record.__dict__.get(cls.KEY, None):
            return item

        # core: Fall back to the current scope.
        if scope := ActivityScope.peek():
            return cls(
                scope=scope.name,
                frame=scope.frame,
                trace_id=scope.trace_id,
                span_id=scope.span_id,
                parent_id=scope.parent_id,
                elapsed=scope.elapsed.current,
                state=scope.state
            )

        # core: There was nothing to get.
        return None
