import dataclasses
import inspect
import logging
import sys
import uuid
from enum import Enum
from typing import Any, Optional, Iterator

from _reusable import Elapsed
from wiretap.data import Activity, WIRETAP_KEY, Trace, Entry


class ActivityScope(Activity):
    """
    This class represents an activity for which telemetry is collected.
    """

    def __init__(
            self,
            parent: Optional["ActivityScope"],
            name: str,
            frame: inspect.FrameInfo,
            snapshot: dict[str, Any] | None = None,
            tags: set[str | Enum] | None = None,
            **kwargs: Any
    ):
        self.parent = parent
        self.id = uuid.uuid4()
        self.name = name
        self.frame = frame
        self.snapshot = (snapshot or {}) | kwargs
        self.tags = tags or set()
        self.elapsed = Elapsed()
        self.in_progress = True
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
            name: str,
            message: str | None = None,
            snapshot: dict | None = None,
            tags: set[str | Enum] | None = None,
            exc_info: bool = False,
            in_progress: bool = True,
            **kwargs
    ) -> None:
        if not self.in_progress:
            if in_progress:
                raise Exception(f"The current '{self.name}' activity is no longer in progress.")
            else:
                return

        tags = (tags or set()) | self.tags
        self.logger.log(
            level=logging.INFO,
            msg=message,
            exc_info=exc_info,
            extra={
                WIRETAP_KEY: Entry(
                    activity=self,
                    trace=Trace(name=name, message=message),
                    note=(snapshot or {}) | kwargs,
                    tags=tags
                )
            }
        )
        if not in_progress:
            self.in_progress = False

    def log_info(
            self,
            message: str | None = None,
            snapshot: dict | None = None,
            tags: set[str | Enum] | None = None,
            **kwargs
    ) -> None:
        """This function logs any state."""
        self.log_trace(
            name="info",
            message=message,
            snapshot=snapshot,
            tags=tags,
            in_progress=True,
            **kwargs
        )

    def log_metric(
            self,
            message: str | None = None,
            snapshot: dict | None = None,
            tags: set[str | Enum] | None = None,
            **kwargs
    ) -> None:
        """This function logs any state."""
        self.log_trace(
            name="metric",
            message=message,
            snapshot=snapshot,
            tags=tags,
            in_progress=True,
            **kwargs
        )

    def log_branch(
            self,
            message: str,
            snapshot: dict | None = None,
            tags: set[str | Enum] | None = None,
            **kwargs
    ) -> None:
        """This function logs conditional branches."""
        self.log_trace(
            name="branch",
            message=message,
            snapshot=snapshot,
            tags=tags,
            in_progress=True,
            **kwargs
        )

    def log_end(
            self,
            message: str | None = None,
            snapshot: dict | None = None,
            tags: set[str | Enum] | None = None,
            **kwargs
    ) -> None:
        """This function logs a regular end of an activity."""
        self.log_trace(
            name="end",
            message=message,
            snapshot=(snapshot or {}) | self.snapshot,
            tags=tags,
            in_progress=False,
            **kwargs
        )

    def log_exit(
            self,
            message: str | None = None,
            snapshot: dict | None = None,
            tags: set[str | Enum] | None = None,
            **kwargs
    ) -> None:
        """This function logs an unusual end of an activity."""
        self.log_trace(
            name="exit",
            message=message,
            snapshot=(snapshot or {}) | self.snapshot,
            tags=tags,
            in_progress=False,
            **kwargs
        )

    def log_error(
            self,
            message: str | None = None,
            snapshot: dict | None = None,
            tags: set[str | Enum] | None = None,
            exc_info: bool = True,
            **kwargs
    ) -> None:
        """This function logs an error in an activity."""
        exc_cls, exc, exc_tb = sys.exc_info()
        snapshot = snapshot or {}
        if exc_cls:
            snapshot["reason"] = exc_cls.__name__
            # snapshot["message"] = str(exc) or None
        self.log_trace(
            name="error",
            message=message or str(exc) or None,
            snapshot=(snapshot or {}) | self.snapshot,
            tags=tags,
            exc_info=exc_info,
            in_progress=False,
            **kwargs
        )
