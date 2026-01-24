import contextlib
import logging
import secrets
from contextvars import ContextVar  # noqa: built-in module
from enum import Enum
from functools import reduce
from inspect import FrameInfo
from typing import Optional, Any, Iterator, TypeVar, ClassVar, Literal

from wiretap.util.stopwatch import Stopwatch

T = TypeVar("T", bound="Span")

TRACE_LEVEL = 5

LogLevelName = Literal["off", "trace", "debug", "info", "warning", "error", "critical"]


class SpanStatus(str, Enum):
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"

    def __str__(self):
        return self.value


class NoSpanInScopeError(Exception):
    pass


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
        self.operation: str = name or frame.function
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
# @dataclasses.dataclass
class SpanEvent:
    KEY = "_span_event"

    def __init__(self, span: Span, frame: FrameInfo | None = None, state: dict[str, Any] | None = None, **kwargs):
        self.operation = span.operation
        self.frame = frame
        self.depth = span.depth
        self.trace_id = span.trace_id
        self.span_id = span.span_id
        self.parent_id = span.parent_id
        self.stopwatch = span.stopwatch
        # core: Merge the state of all scopes.
        self.state = reduce(lambda c, n: (n.state or {}) | c, span, (state or {}) | kwargs)
        self.status = span.status
