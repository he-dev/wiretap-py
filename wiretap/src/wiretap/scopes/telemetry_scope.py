import contextlib
import dataclasses
import logging
import uuid
from contextvars import ContextVar
from inspect import FrameInfo
from typing import Optional, Any, Iterator, Callable

from tools import Elapsed
from wiretap.data import TagSet


class TelemetryScope:
    """
    This class represents a single telemetry scope.
    """

    current_scope: ContextVar[Optional["TelemetryScope"]] = ContextVar("current_scope", default=None)

    def __init__(
            self,
            id: Any | None,
            name: str | None,
            tags: set[Any] | None,
            frame: FrameInfo,
            parent: Optional["TelemetryScope"]
    ):
        self.id = id or uuid.uuid4()
        self.name = name or frame.function
        self.tags = tags or set()
        self.frame = frame
        self.depth = 1
        self.parent = parent

        if parent:
            self.tags = self.tags | parent.tags
            self.depth = self.depth + parent.depth

        self.elapsed = Elapsed()
        self.logger: logging.Logger = logging.getLogger(name)

        self.trace_count_own: int = 0
        self.trace_count_all: int = 0

    def log_trace(
            self,
            level: int,
            msg: str,
            exc_info: bool,
            extra: "TelemetryItem",
    ) -> None:
        self.logger.log(
            level=level,
            msg=msg,
            exc_info=exc_info,
            extra=extra.to_extra()
        )
        self.trace_count_own += 1
        self.trace_count_all += 1

    def __iter__(self) -> Iterator["TelemetryScope"]:
        current: Optional["TelemetryScope"] = self
        while current:
            yield current
            current = current.parent

    @classmethod
    @contextlib.contextmanager
    def push(
            cls,
            id: Any | None,
            name: str | None,
            tags: set[Any] | None,
            frame: FrameInfo
    ) -> Iterator["TelemetryScope"]:
        parent = cls.peek()
        scope = cls(id=id, name=name, tags=tags, frame=frame, parent=parent)
        token = cls.current_scope.set(scope)
        try:
            yield scope
        finally:
            if parent:
                parent.trace_count_all += scope.trace_count_all
            cls.current_scope.reset(token)

    @classmethod
    def peek(cls) -> Optional["TelemetryScope"]:
        return cls.current_scope.get()


@dataclasses.dataclass
class TelemetryTrace:
    name: str | None
    message: str | None
    state: dict[str, Any]
    tags: TagSet
    is_final: bool


@dataclasses.dataclass
class TelemetryItem:
    """This takes care of the extra data that is added to the log record."""

    KEY = "_telemetry"

    scope: TelemetryScope
    trace: TelemetryTrace | None

    def to_extra(self) -> dict[str, Any]:
        return {
            self.KEY: TelemetryItem(
                self.scope,
                self.trace,
            )
        }

    @classmethod
    def from_record_or_scope(cls, record: logging.LogRecord) -> Optional["TelemetryItem"]:
        # Try to get telemetry scope and trace from the record.
        item: Optional["TelemetryItem"] = record.__dict__.get(cls.KEY, None)
        if item:
            return item

        # Try to get the closest telemetry scope.
        scope = TelemetryScope.peek()
        if scope:
            return cls(scope, None)

        # There was nothing to get.
        return None
