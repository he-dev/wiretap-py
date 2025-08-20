import contextlib
import dataclasses
import inspect
import logging
import secrets
import sys
from contextvars import ContextVar  # noqa: built-in module
from functools import reduce
from inspect import FrameInfo
from typing import Optional, Any, Iterator, TypeVar, ClassVar

from wiretap.core import NoSpanInScopeError, SpanStatus
from wiretap.meta import LogLevelName, map_level_name_to_int
from wiretap.util.stopwatch import Stopwatch

T = TypeVar("T", bound="Span")


class Span:
    """
    This class represents a single activity scope.
    """

    _current: ClassVar[ContextVar[Optional["Span"]]] = ContextVar("current_span", default=None)

    def __init__(
            self,
            trace_id: Any | None,
            parent_id: Any | None,
            name: str | None,
            state: dict[str, Any] | None,
            frame: FrameInfo,
            parent: Optional["Span"],
            **kwargs,
    ):
        self.trace_id: str = trace_id or (parent.trace_id if parent else secrets.token_hex(16))
        self.span_id: str = secrets.token_hex(8)
        self.parent_id: str | None = parent_id or (parent.span_id if parent else None)
        self.name: str = name or frame.function
        self.state: dict = (state or {}) | kwargs
        self.status: SpanStatus = SpanStatus.UNSET
        self.frame: FrameInfo = frame
        self.depth: int = 0 if parent is None else parent.depth + 1
        self.parent: Optional["Span"] = parent
        self.stopwatch: Stopwatch = Stopwatch()
        self.logger: logging.Logger = logging.getLogger(name)

    def __iter__(self) -> Iterator["Span"]:
        current: Optional["Span"] = self
        while current:
            yield current
            current = current.parent

    @staticmethod
    def log_event(
            message: str | None = None,
            level: LogLevelName = "info",
            state: dict | None = None,
            frame_at: int | None = None,
            **kwargs
    ) -> None:

        _level = map_level_name_to_int(level)

        if scope := Span.current():
            stack = inspect.stack(2)
            frame = stack[frame_at] if frame_at else scope.frame

            scope.logger.log(
                level=_level,
                msg=message,
                exc_info=_level >= logging.ERROR or sys.exc_info()[0] is not None,
                extra={
                    SpanEvent.KEY: SpanEvent(scope=scope, frame=frame, state=state, **kwargs)
                }
            )
        else:
            raise NoSpanInScopeError("Cannot log event because there is no activity in scope.")

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
        :param trace_id: The trace ID to use for the scope. If None, a random ID will be generated.
        :param parent_id: The parent ID to use for the scope. If None, the parent ID will be derived from the parent scope.
        :param state: Extra data to attach to the scope.
        :param frame: Frame information about the scope’s context.

        :returns: The newly created scope.
        """

        if frame is None:
            raise ValueError("FrameInfo must not be None.")

        parent = cls.current()
        scope = cls(name=name, trace_id=trace_id, parent_id=parent_id, state=state, frame=frame, parent=parent, **kwargs)
        token = cls._current.set(scope)
        try:
            yield scope
        finally:
            cls._current.reset(token)

    # note: There is no builtin @classproperty! :-\
    @classmethod
    def current(cls) -> Optional["Span"]:
        return cls._current.get()


# util: Collects all the data for logging in one place.
@dataclasses.dataclass
class SpanEvent:
    KEY = "_span_event"

    def __init__(self, scope: Span, frame: FrameInfo | None = None, state: dict[str, Any] | None = None, **kwargs):
        self.name = scope.name
        self.frame = frame
        self.depth = scope.depth
        self.trace_id = scope.trace_id
        self.span_id = scope.span_id
        self.parent_id = scope.parent_id
        self.stopwatch = scope.stopwatch
        # core: Merge the state of all scopes.
        self.state = reduce(lambda c, n: (n.state or {}) | c, scope, (state or {}) | kwargs)
        self.status = scope.status
