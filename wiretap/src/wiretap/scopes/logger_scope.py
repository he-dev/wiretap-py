import contextlib
import inspect
import logging
import threading
import uuid
from inspect import FrameInfo
from collections import defaultdict
from contextvars import ContextVar
from typing import Any, Optional, Iterator, Tuple, Union

from _reusable import Elapsed, map_to_str
from wiretap.data import LoggerItem, LoggerTrace, TraceTag

procedure_calls: ContextVar[dict[Tuple[str, ...], int]] = ContextVar("procedure_calls", default=defaultdict(lambda: 0))

SCOPE_KEY = "_scope"
TRACE_KEY = "_trace"


class LoggerScope(LoggerItem["LoggerScope"]):
    """
    This class represents a procedure for which telemetry is collected.
    """

    current_scope: ContextVar[Optional["LoggerScope"]] = ContextVar("current_scope", default=None)

    lock = threading.Lock()

    def __init__(
            self,
            id: Any | None,
            name: str,
            tags: set[Any] | None,
            frame: FrameInfo,
            parent: Optional["LoggerScope"]
    ):
        self.parent = parent
        self.id = id or uuid.uuid4()
        self.name = name or frame.function
        # self.state: dict[str, Any] = (parent.state if parent else {}) | (state or {}) | kwargs
        self.tags: set[str] = (parent.tags if parent else map_to_str(tags)) | map_to_str(tags)
        self.frame = frame
        self.elapsed = Elapsed()
        self.can_log = True
        self.logger = logging.getLogger(name)
        self.depth: int = parent.depth + 1 if parent else 1

        with LoggerScope.lock:
            key = tuple((p.name for p in self))
            calls = procedure_calls.get()
            calls[key] += 1
            self.times = calls[key]

    def __iter__(self) -> Iterator["LoggerScope"]:
        current: Optional["LoggerScope"] = self
        while current:
            yield current
            current = current.parent

    def log_trace(
            self,
            name: str | None = None,
            message: str | None = None,
            state: dict | None = None,
            tags: set[Any] | None = None,
            exc_info: bool = False,
            is_final: bool = False,
            level: int = logging.DEBUG,
            **kwargs
    ) -> None:
        """This function logs a single trace."""

        # Can no longer log.
        if not self.can_log:
            # Ignore logs from other final logs.
            if is_final:
                return
            # Logging non-final logs is otherwise illegal.
            else:
                raise Exception(f"The current scope '{self.name}' can no longer log.")

        self.logger.log(
            level=level,
            msg=message,
            exc_info=exc_info,
            extra={
                SCOPE_KEY: self,
                TRACE_KEY: LoggerTrace(
                    name=name,
                    message=message,
                    state=(state or {}) | kwargs,
                    tags=map_to_str(tags),
                )
            }
        )
        
        if is_final:
            self.can_log = False

    def log_info(
            self,
            name: str = "info",
            message: str | None = None,
            state: dict | None = None,
            tags: set[Any] | None = None,
            is_final: bool = False,
            **kwargs
    ) -> None:
        """This function logs some additional information."""
        self.log_trace(
            name,
            message=message,
            state=state,
            tags=tags,
            is_final=is_final,
            level=logging.INFO,
            **kwargs
        )

    def log_debug(
            self,
            name: str = "debug",
            message: str | None = None,
            state: dict | None = None,
            tags: set[Any] | None = None,
            is_final: bool = False,
            **kwargs
    ) -> None:
        """This function logs some additional information."""
        self.log_trace(
            name=name,
            message=message,
            state=state,
            tags=tags,
            is_final=is_final,
            level=logging.DEBUG,
            **kwargs
        )

    def log_error(
            self,
            message: str | None = None,
            state: dict | None = None,
            tags: set[Any] | None = None,
            **kwargs
    ) -> None:
        """This function logs an error in the procedure."""
        self.log_trace(
            name="error",
            message=message,
            state=state,
            tags=(tags or set()) | {TraceTag.EVENT},
            level=logging.ERROR,
            is_final=True,
            **kwargs
        )

    def log_exception(
            self,
            tags: set[Any] | None = None,
    ) -> None:
        """This function logs an error in the procedure."""
        self.log_trace(
            name="exception",
            tags=tags,
            exc_info=True,
            level=logging.CRITICAL,
            is_final=True
        )

    @classmethod
    @contextlib.contextmanager
    def push(
            cls,
            id: Any | None,
            name: str,
            tags: set[Any] | None,
            frame: FrameInfo
    ) -> Iterator["LoggerScope"]:
        parent = cls.peek()
        scope = cls(id=id, name=name, tags=tags, frame=frame, parent=parent)
        token = cls.current_scope.set(scope)
        try:
            yield scope
        finally:
            cls.current_scope.reset(token)

    @classmethod
    def peek(cls) -> Optional["LoggerScope"]:
        return cls.current_scope.get()


def logger_scope(record: logging.LogRecord) -> LoggerScope | None:
    # Try to get the feed from the record first otherwise the closest one.
    return record.__dict__.get(SCOPE_KEY, None) or LoggerScope.peek()


def logger_trace(record: logging.LogRecord) -> LoggerTrace | None:
    # Try to get the feed from the record first otherwise the closest one.
    return record.__dict__.get(TRACE_KEY, None)
