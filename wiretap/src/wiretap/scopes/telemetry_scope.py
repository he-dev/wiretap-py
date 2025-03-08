import contextlib
import dataclasses
import logging
import uuid
from contextvars import ContextVar
from inspect import FrameInfo
from typing import Optional, Any, Iterator

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
        self.can_log = True

        if parent:
            self.tags |= parent.tags
            self.depth += parent.depth

        self.elapsed = Elapsed()
        self.logger: logging.Logger = logging.getLogger(name)

        # Counts traces logged by this scope only.
        self.trace_count_own: int = 0

        # Counts traces logged by this scope and its children.
        self.trace_count_all: int = 0

    def __iter__(self) -> Iterator["TelemetryScope"]:
        current: Optional["TelemetryScope"] = self
        while current:
            yield current
            current = current.parent

    @property
    def is_debug(self) -> bool:
        return self.logger.isEnabledFor(logging.DEBUG)

    def log_trace(
            self,
            event: str,
            message: str | None = None,
            dump: dict | None = None,
            tags: set[Any] | None = None,
            level: int = logging.DEBUG,
            exc_info: bool = False,
            is_final: bool = False,
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
            extra=TelemetryItem(
                scope=self,
                trace=TelemetryTrace(
                    event=event,
                    message=message,
                    dump=(dump or {}) | kwargs,
                    tags=TagSet(tags),
                    is_final=is_final,
                )
            ).to_extra()
        )

        # Increment counters if logged.
        if self.logger.isEnabledFor(level):
            self.trace_count_own += 1
            self.trace_count_all += 1

        self.can_log = not is_final

    def log_basic(
            self,
            event: str = "info",
            message: str | None = None,
            dump: dict | None = None,
            tags: set[Any] | None = None,
            is_final: bool = False,
            **kwargs
    ) -> None:
        """
        Logs info trace at the info level.
        """
        self.log_trace(
            event=event,
            message=message,
            dump=dump,
            tags=tags,
            level=logging.INFO,
            is_final=is_final,
            **kwargs
        )

    def log_debug(
            self,
            event: str = "info",
            message: str | None = None,
            dump: dict | None = None,
            tags: set[Any] | None = None,
            is_final: bool = False,
            **kwargs
    ) -> None:
        """
        Logs info trace at the debug level.
        """
        self.log_trace(
            event=event,
            message=message,
            dump=dump,
            tags=tags,
            level=logging.DEBUG,
            is_final=is_final,
            **kwargs
        )

    def log_error(
            self,
            message: str | None = None,
            dump: dict | None = None,
            tags: set[Any] | None = None,
            is_final: bool = True,
            **kwargs
    ) -> None:
        """This function logs an error in the procedure."""
        self.log_trace(
            event="error",
            message=message,
            dump=dump,
            tags=(tags or set()),
            level=logging.ERROR,
            is_final=is_final,
            **kwargs
        )

    def log_exception(
            self,
            dump: dict | None = None,
            tags: set[Any] | None = None,
            is_final: bool = True,
            **kwargs
    ) -> None:
        """This function logs an error in the procedure."""
        self.log_trace(
            event="exception",
            tags=tags,
            dump=dump,
            level=logging.CRITICAL,
            exc_info=True,
            is_final=is_final,
            **kwargs
        )

    @classmethod
    @contextlib.contextmanager
    def push(
            cls,
            id: Any | None,
            name: str | None,
            tags: set[Any] | None,
            frame: FrameInfo
    ) -> Iterator["TelemetryScope"]:
        """
        Pushes a new telemetry scope onto the stack.

        Parameters:
        - id (Optional[Any]): Identifier for the scope, autogenerated if none provided.
        - name (Optional[str]): Name of the scope, derived from the calling frame if none provided.
        - tags (Optional[set[Any]]): Tags to associate with this telemetry scope.
        - frame (FrameInfo): Frame information about the scope’s context.

        Yields:
        - TelemetryScope: The newly created scope.
        """

        if frame is None:
            raise ValueError("FrameInfo must not be None.")

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
    event: str | None
    message: str | None
    dump: dict[str, Any]
    tags: TagSet
    is_final: bool


@dataclasses.dataclass
class TelemetryItem:
    """
    This class takes care of the extra data that is added to the log record.
    """

    KEY = "_telemetry"

    scope: TelemetryScope | None
    trace: TelemetryTrace | None

    @property
    def properties(self) -> tuple[Optional[TelemetryScope], Optional[TelemetryTrace]]:
        return self.scope, self.trace

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
        return TelemetryItem(None, None)

    def __bool__(self) -> bool:
        return bool(self.scope or self.trace)
