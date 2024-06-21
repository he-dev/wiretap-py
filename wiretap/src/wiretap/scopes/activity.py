import contextlib
import inspect
import logging
import sys
import uuid
from typing import Any, Optional, Iterator

from _reusable import Elapsed, map_to_str
from wiretap.data import Activity, WIRETAP_KEY, Trace, Entry, Correlation
from wiretap.scopes.loop import LoopScope


class ActivityScope(Activity):
    """
    This class represents an activity for which telemetry is collected.
    """

    def __init__(
            self,
            parent: Optional["ActivityScope"],
            func: str,
            name: str | None,
            frame: inspect.FrameInfo,
            extra: dict[str, Any] | None = None,
            tags: set[Any] | None = None,
            correlation: Correlation | None = None,
            **kwargs: Any
    ):
        self.parent = parent
        self.id = uuid.uuid4()
        self.func = func
        self.name = name
        self.frame = frame
        self.extra = (extra or {}) | kwargs
        self.tags: set[str] = map_to_str(tags)
        self.elapsed = Elapsed()
        self.in_progress = True
        self.correlation = correlation or Correlation(self.id, type="default")
        self.logger = logging.getLogger(name)

    @property
    def depth(self) -> int:
        return self.parent.depth + 1 if self.parent else 1

    def __iter__(self) -> Iterator["ActivityScope"]:
        current: Optional["ActivityScope"] = self
        while current:
            yield current
            current = current.parent

    def log_trace(
            self,
            code: str,
            name: str | None = None,
            message: str | None = None,
            extra: dict | None = None,
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
                    extra=(extra or {}) | kwargs,
                    tags=map_to_str(tags) | self.tags,
                )
            }
        )
        if not in_progress:
            self.in_progress = False

    def log_snapshot(
            self,
            name: str | None = None,
            message: str | None = None,
            extra: dict | None = None,
            tags: set[str] | None = None,
            **kwargs
    ) -> None:
        """This function logs any state."""

        if not extra and not kwargs:
            raise ValueError("Snapshot trace requires 'extra' arguments.")

        self.log_trace(
            code="snapshot",
            name=name,
            message=message,
            extra=extra,
            tags=tags,
            in_progress=True,
            **kwargs
        )

    def log_metric(
            self,
            name: str | None = None,
            message: str | None = None,
            extra: dict | None = None,
            tags: set[str] | None = None,
            **kwargs
    ) -> None:
        """This function logs any state."""

        if not extra and not kwargs:
            raise ValueError("Metric trace requires 'extra' arguments.")

        self.log_trace(
            code="metric",
            name=name,
            message=message,
            extra=extra,
            tags=tags,
            in_progress=True,
            **kwargs
        )

    def log_info(
            self,
            name: str | None = None,
            message: str | None = None,
            extra: dict | None = None,
            tags: set[str] | None = None,
            **kwargs
    ) -> None:
        """This function logs conditional branches."""
        self.log_trace(
            code="info",
            name=name,
            message=message,
            extra=extra,
            tags=tags,
            in_progress=True,
            **kwargs
        )

    def log_branch(
            self,
            name: str,
            message: str | None = None,
            extra: dict | None = None,
            tags: set[str] | None = None,
            **kwargs
    ) -> None:
        """This function logs conditional branches."""
        self.log_trace(
            code="branch",
            name=name,
            message=message,
            extra=extra,
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
            **kwargs,
    ) -> Iterator[LoopScope]:
        """This function initializes a new scope for loop telemetry."""
        loop = LoopScope()
        try:
            yield loop
        finally:
            self.log_trace(
                code="loop",
                name=name,
                message=message,
                extra=loop.dump(),
                tags=tags,
                **kwargs
            )

    def log_end(
            self,
            message: str | None = None,
            extra: dict | None = None,
            tags: set[str] | None = None,
            **kwargs
    ) -> None:
        """This function logs a regular end of an activity."""
        self.log_trace(
            code="end",
            message=message,
            extra=(extra or {}) | self.extra,
            tags=tags,
            in_progress=False,
            **kwargs
        )

    def log_exit(
            self,
            message: str | None = None,
            extra: dict | None = None,
            tags: set[str] | None = None,
            **kwargs
    ) -> None:
        """This function logs an unusual end of an activity."""
        self.log_trace(
            code="exit",
            message=message,
            extra=(extra or {}) | self.extra,
            tags=tags,
            in_progress=False,
            **kwargs
        )

    def log_error(
            self,
            message: str | None = None,
            extra: dict | None = None,
            tags: set[str] | None = None,
            exc_info: bool = True,
            **kwargs
    ) -> None:
        """This function logs an error in an activity."""
        exc_cls, exc, exc_tb = sys.exc_info()
        extra = extra or {}
        if exc_cls:
            extra["reason"] = exc_cls.__name__
            # snapshot["message"] = str(exc) or None
        self.log_trace(
            code="error",
            message=message or str(exc) or None,
            extra=(extra or {}) | self.extra,
            tags=tags,
            exc_info=exc_info,
            in_progress=False,
            **kwargs
        )
