import contextlib
import inspect
import logging
import sys
import threading
import uuid
from collections import defaultdict
from contextvars import ContextVar
from typing import Any, Optional, Iterator, Tuple

from _reusable import Elapsed, map_to_str
from wiretap.contexts.iteration import IterationContext
from wiretap.data import Procedure, WIRETAP_KEY, Trace, Entry, Execution

procedure_calls: ContextVar[dict[Tuple[str, ...], int]] = ContextVar("procedure_calls", default=defaultdict(lambda: 0))


class ProcedureContext(Procedure):
    """
    This class represents an activity for which telemetry is collected.
    """

    lock = threading.Lock()

    def __init__(
            self,
            func: str,
            file: str,
            line: int,
            parent: Optional["ProcedureContext"],
            name: str,
            data: dict[str, Any] | None,
            tags: set[Any] | None,
            **kwargs: Any
    ):
        self.parent = parent
        self.id = uuid.uuid4()
        self.name = name
        self.data: dict[str, Any] = (parent.data if parent else {}) | (data or {}) | kwargs
        self.tags: set[str] = (parent.tags if parent else map_to_str(tags)) | map_to_str(tags)
        self.func = func
        self.file = file
        self.line = line
        self.elapsed = Elapsed()
        self.in_progress = True
        self.logger = logging.getLogger(name)
        self.depth: int = parent.depth + 1 if parent else 1
        self.trace_count: int = 0
        with ProcedureContext.lock:
            key = tuple((p.name for p in self))
            calls = procedure_calls.get()
            calls[key] += 1
            self.times = calls[key]

    @property
    def execution(self) -> Execution:
        return Execution(self)

    def __iter__(self) -> Iterator["ProcedureContext"]:
        current: Optional["ProcedureContext"] = self
        while current:
            yield current
            current = current.parent

    def log_trace(
            self,
            name: str | None = None,
            message: str | None = None,
            data: dict | None = None,
            tags: set[Any] | None = None,
            exc_info: bool = False,
            in_progress: bool = True,
            **kwargs
    ) -> None:
        if not self.in_progress:
            if in_progress:
                raise Exception(f"The current '{self.name}' activity is no longer in progress.")
            else:
                return

        self.trace_count += 1
        self.logger.log(
            level=logging.INFO,
            msg=message,
            exc_info=exc_info,
            extra={
                WIRETAP_KEY: Entry(
                    procedure=self,
                    trace=Trace(
                        name=name,
                        message=message,
                        data=(data or {}) | kwargs,
                        tags=map_to_str(tags),
                    )
                )
            }
        )
        if not in_progress:
            self.in_progress = False

    def log_snapshot(
            self,
            message: str | None = None,
            data: dict | None = None,
            tags: set[str] | None = None,
            **kwargs
    ) -> None:
        """This function logs any state."""

        if not data and not kwargs:
            raise ValueError("Snapshot trace requires 'data'.")

        self.log_trace(
            name="snapshot",
            message=message,
            data=data,
            tags=tags,
            in_progress=True,
            **kwargs
        )

    def log_metric(
            self,
            message: str | None = None,
            data: dict | None = None,
            tags: set[str] | None = None,
            **kwargs
    ) -> None:
        """This function logs any state."""

        if not data and not kwargs:
            raise ValueError("Metric trace requires 'body'.")

        self.log_trace(
            name="metric",
            message=message,
            data=data,
            tags=tags,
            in_progress=True,
            **kwargs
        )

    def log_info(
            self,
            message: str | None = None,
            data: dict | None = None,
            tags: set[str] | None = None,
            **kwargs
    ) -> None:
        """This function logs conditional branches."""
        self.log_trace(
            name="info",
            message=message,
            data=data,
            tags=tags,
            in_progress=True,
            **kwargs
        )

    def log_branch(
            self,
            message: str | None = None,
            data: dict | None = None,
            tags: set[str] | None = None,
            **kwargs
    ) -> None:
        """This function logs conditional branches."""
        self.log_trace(
            name="branch",
            message=message,
            data=data,
            tags=tags,
            in_progress=True,
            **kwargs
        )

    @contextlib.contextmanager
    def log_loop(
            self,
            message: str | None = None,
            tags: set[str] | None = None,
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
                tags=(tags or set()) | {"loop"},
                **kwargs
            )

    def log_last(
            self,
            name: str,
            message: str | None = None,
            data: dict | None = None,
            tags: set[str] | None = None,
            exc_info: bool = False,
            **kwargs
    ) -> None:
        """This function logs a regular end of an activity."""
        exc_cls, exc, exc_tb = sys.exc_info()
        if exc_cls:
            data = (data or {}) | {"reason": exc_cls.__name__}

        self.log_trace(
            name=name,
            message=message,
            data=data,
            tags=tags,
            exc_info=exc_info,
            in_progress=False,
            **kwargs
        )

    def log_error(
            self,
            message: str | None = None,
            data: dict | None = None,
            tags: set[str] | None = None,
            exc_info: bool = True,
            **kwargs
    ) -> None:
        """This function logs an error in an activity."""
        self.log_last(
            name="error",
            message=message,
            data=data,
            tags=tags,
            exc_info=exc_info,
            **kwargs
        )
