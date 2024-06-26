import contextlib
import inspect
import logging
import sys
import uuid
from typing import Any, Optional, Iterator

from _reusable import Elapsed, map_to_str
from wiretap.contexts.iteration import IterationContext
from wiretap.data import Activity, WIRETAP_KEY, Trace, Entry, Correlation


class ActivityContext(Activity):
    """
    This class represents an activity for which telemetry is collected.
    """

    def __init__(
            self,
            parent: Optional["ActivityContext"],
            func: str,
            name: str | None,
            frame: inspect.FrameInfo,
            body: dict[str, Any] | None = None,
            tags: set[Any] | None = None,
            correlation: Correlation | None = None,
            **kwargs: Any
    ):
        self.parent = parent
        self.id = uuid.uuid4()
        self.func = func
        self.name = name
        self.frame = frame
        self.body = (body or {}) | kwargs
        self.tags: set[str] = map_to_str(tags) | parent.tags if parent else map_to_str(tags)
        self.elapsed = Elapsed()
        self.in_progress = True
        self.correlation = correlation or Correlation(self.id, type="default")
        self.logger = logging.getLogger(name)
        self.depth = parent.depth + 1 if parent else 0
        self.context = parent.context | self.body if parent else self.body

    def __iter__(self) -> Iterator["ActivityContext"]:
        current: Optional["ActivityContext"] = self
        while current:
            yield current
            current = current.parent

    def log_trace(
            self,
            code: str,
            name: str | None = None,
            message: str | None = None,
            body: dict | None = None,
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

        self.logger.log(
            level=logging.INFO,
            msg=message,
            exc_info=exc_info,
            extra={
                WIRETAP_KEY: Entry(
                    activity=self,
                    trace=Trace(code=code, name=name, message=message),
                    body=(body or {}) | kwargs,
                    tags=map_to_str(tags),
                )
            }
        )
        if not in_progress:
            self.in_progress = False

    def log_snapshot(
            self,
            name: str | None = None,
            message: str | None = None,
            body: dict | None = None,
            tags: set[str] | None = None,
            **kwargs
    ) -> None:
        """This function logs any state."""

        if not body and not kwargs:
            raise ValueError("Snapshot trace requires 'body'.")

        self.log_trace(
            code="snapshot",
            name=name,
            message=message,
            body=body,
            tags=tags,
            in_progress=True,
            **kwargs
        )

    def log_metric(
            self,
            name: str | None = None,
            message: str | None = None,
            body: dict | None = None,
            tags: set[str] | None = None,
            **kwargs
    ) -> None:
        """This function logs any state."""

        if not body and not kwargs:
            raise ValueError("Metric trace requires 'body'.")

        self.log_trace(
            code="metric",
            name=name,
            message=message,
            body=body,
            tags=tags,
            in_progress=True,
            **kwargs
        )

    def log_info(
            self,
            name: str | None = None,
            message: str | None = None,
            body: dict | None = None,
            tags: set[str] | None = None,
            **kwargs
    ) -> None:
        """This function logs conditional branches."""
        self.log_trace(
            code="info",
            name=name,
            message=message,
            body=body,
            tags=tags,
            in_progress=True,
            **kwargs
        )

    def log_branch(
            self,
            name: str,
            message: str | None = None,
            body: dict | None = None,
            tags: set[str] | None = None,
            **kwargs
    ) -> None:
        """This function logs conditional branches."""
        self.log_trace(
            code="branch",
            name=name,
            message=message,
            body=body,
            tags=tags,
            in_progress=True,
            **kwargs
        )

    @contextlib.contextmanager
    def log_loop(
            self,
            name: str,
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
            self.log_trace(
                code="loop",
                name=name,
                message=message,
                body=loop.dump(),
                tags=tags,
                **kwargs
            )

    def log_last(
            self,
            code: str,
            message: str | None = None,
            body: dict | None = None,
            tags: set[str] | None = None,
            exc_info: bool = False,
            **kwargs
    ) -> None:
        """This function logs a regular end of an activity."""
        exc_cls, exc, exc_tb = sys.exc_info()
        if exc_cls:
            body = (body or {}) | {"reason": exc_cls.__name__}

        self.log_trace(
            code=code,
            message=message,
            body=(body or {}) | self.body,
            tags=tags,
            exc_info=exc_info,
            in_progress=False,
            **kwargs
        )

    def log_error(
            self,
            message: str | None = None,
            body: dict | None = None,
            tags: set[str] | None = None,
            exc_info: bool = True,
            **kwargs
    ) -> None:
        """This function logs an error in an activity."""
        self.log_last(
            code="error",
            message=message,
            body=(body or {}) | self.body,
            tags=tags,
            exc_info=exc_info,
            **kwargs
        )
