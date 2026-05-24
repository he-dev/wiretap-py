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

    _stack: ClassVar[ContextVar[Optional["Span"]]] = ContextVar("current_span", default=None)

    def __init__(
            self,
            name: str | None,
            state: dict[str, Any] | None,
            trace_id: Any | None,
            parent_id: Any | None,
            frame: FrameInfo,
            **kwargs,
    ):
        """
        Initialize a new Span instance.

        Args:
            name: The name of the span.
            state: The initial state of the span.
            trace_id: The trace ID for the span.
            parent_id: The parent span ID.
            frame: The frame information for the span.
            **kwargs: Additional keyword arguments.
        """

        self.trace_id: str = trace_id or secrets.token_hex(16)
        # note: Cannot use id because it's reserved by python.
        self.span_id: str = secrets.token_hex(8)
        self.parent_id: str | None = parent_id
        self.operation: str = name or frame.function
        self.state: dict = (state or {}) | kwargs
        self.status: SpanStatus = SpanStatus.UNSET
        self.frame: FrameInfo = frame
        self.parent: Optional["Span"] = None
        self.stopwatch: Stopwatch = Stopwatch()
        self.logger: logging.Logger = logging.getLogger(name)

    def __iter__(self) -> Iterator["Span"]:
        current: Optional["Span"] = self
        while current:
            yield current
            current = current.parent

    @property
    def depth(self) -> int:
        return self.parent.depth + 1 if self.parent else 0

    @contextlib.contextmanager
    def push(self) -> Iterator["Span"]:
        """
        Pushes the current span onto the stack.
        """

        if parent := Span.current():
            self.parent = parent
            # core: Set the parent_id only when it is not overridden by a custom value.
            if self.parent_id is None:
                self.parent_id = parent.span_id

        token = Span._stack.set(self)
        try:
            yield self
        finally:
            Span._stack.reset(token)
            self.parent = None

    # note: There is no builtin @classproperty! :-\
    @classmethod
    def current(cls) -> Optional["Span"]:
        return cls._stack.get()


class SpanEvent:
    """This class represents a single span event containing both the span and the event states."""

    KEY = "_span_event"

    def __init__(self, span: Span, frame: FrameInfo | None = None, state: dict[str, Any] | None = None, **kwargs):
        self.operation = span.operation
        # core: Merge the state of all scopes.
        self.state = reduce(lambda c, n: (n.state or {}) | c, span, (state or {}) | kwargs)
        self.depth = span.depth
        self.status = span.status
        self.stopwatch = span.stopwatch
        self.span_id = span.span_id
        self.trace_id = span.trace_id
        self.parent_id = span.parent_id
        self.frame = frame

    def to_dict(self) -> dict:
        return {SpanEvent.KEY: self}

    @staticmethod
    def extract_from(record: logging.LogRecord) -> Optional["SpanEvent"]:
        return record.__dict__.get(SpanEvent.KEY, None)
