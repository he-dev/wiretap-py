import contextlib
import inspect
import logging
import threading
import uuid
from inspect import FrameInfo
from collections import defaultdict
from contextvars import ContextVar
from typing import Any, Optional, Iterator, Tuple

from _reusable import Elapsed, map_to_str
from wiretap.contexts.iteration import IterationContext
from wiretap.data import Block, Trace, TraceLevel, TraceTag, BLOCK_KEY, TRACE_KEY

procedure_calls: ContextVar[dict[Tuple[str, ...], int]] = ContextVar("procedure_calls", default=defaultdict(lambda: 0))


class BlockContext(Block):
    """
    This class represents a procedure for which telemetry is collected.
    """

    lock = threading.Lock()

    def __init__(
            self,
            frame: FrameInfo,
            parent: Optional["BlockContext"],
            name: str,
            tags: set[Any] | None
    ):
        self.parent = parent
        self.id = uuid.uuid4()
        self.name = name
        # self.state: dict[str, Any] = (parent.state if parent else {}) | (state or {}) | kwargs
        self.tags: set[str] = (parent.tags if parent else map_to_str(tags)) | map_to_str(tags)
        self.frame = frame
        self.elapsed = Elapsed()
        self.in_progress = True
        self.logger = logging.getLogger(name)
        self.depth: int = parent.depth + 1 if parent else 1
        self.trace_count: int = 0
        self.traces: list[Trace] = []

        with BlockContext.lock:
            key = tuple((p.name for p in self))
            calls = procedure_calls.get()
            calls[key] += 1
            self.times = calls[key]

    def __iter__(self) -> Iterator["BlockContext"]:
        current: Optional["BlockContext"] = self
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
            in_progress: bool = True,
            level: TraceLevel = TraceLevel.DEBUG,
            **kwargs
    ) -> None:
        """This function logs a single trace."""
        if not self.in_progress:
            if in_progress:
                raise Exception(f"The current '{self.name}' activity is no longer in progress.")
            else:
                return

        with BlockContext.lock:
            self.trace_count += 1

        self.logger.log(
            level=level,
            msg=message,
            exc_info=exc_info,
            extra={
                BLOCK_KEY: self,
                TRACE_KEY: Trace(
                    name=name,
                    message=message,
                    state=(state or {}) | kwargs,
                    tags=map_to_str(tags),
                )
            }
        )
        if not in_progress:
            self.in_progress = False

    def log_info(
            self,
            name: str = "info",
            message: str | None = None,
            state: dict | None = None,
            tags: set[Any] | None = None,
            in_progress: bool = True,
            **kwargs
    ) -> None:
        """This function logs some additional information."""
        self.log_trace(
            name,
            message=message,
            state=state,
            tags=tags,
            in_progress=in_progress,
            level=TraceLevel.INFO,
            **kwargs
        )

    def log_debug(
            self,
            name: str = "debug",
            message: str | None = None,
            state: dict | None = None,
            tags: set[Any] | None = None,
            in_progress: bool = True,
            **kwargs
    ) -> None:
        """This function logs some additional information."""
        self.log_trace(
            name=name,
            message=message,
            state=state,
            tags=tags,
            in_progress=in_progress,
            level=TraceLevel.DEBUG,
            **kwargs
        )

    @contextlib.contextmanager
    def log_loop(
            self,
            message: str | None = None,
            tags: set[Any] | None = None,
            counter_name: str | None = None,
            **kwargs,
    ) -> Iterator[IterationContext]:
        """This function initializes a new scope for loop telemetry."""
        loop = IterationContext(counter_name)
        try:
            yield loop
        finally:
            self.log_metric(
                message=message,
                data=loop.dump(),
                tags=(tags or set()) | {TraceTag.LOOP},
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
            level=TraceLevel.ERROR,
            in_progress=False,
            **kwargs
        )

    def log_exception(
            self
    ) -> None:
        """This function logs an error in the procedure."""
        self.log_trace(
            name="exception",
            exc_info=True,
            level=TraceLevel.EXCEPTION,
            in_progress=False
        )
