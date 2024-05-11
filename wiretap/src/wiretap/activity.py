import inspect
import logging

from _reusable import Elapsed


class Activity:
    """
    This class represents an activity for which telemetry is collected.
    """

    def __init__(
            self,
            name: str,
            frame: inspect.FrameInfo
    ):
        self.name = name
        self.frame = frame
        self.elapsed = Elapsed()
        self.in_progress = True
        self.logger = logging.getLogger(name)

    def log_trace(
            self,
            name: str,
            message: str | None = None,
            snapshot: dict | None = None,
            tags: set[str] | None = None,
            exc_info: bool = False,
            in_progress: bool = True
    ) -> None:
        if not self.in_progress:
            if in_progress:
                raise Exception(f"The current '{self.name}' activity is no longer open.")
            else:
                return

        tags = (tags or set())
        self.logger.log(
            level=logging.INFO,
            msg=message,
            exc_info=exc_info,
            extra={
                "trace_message": message,
                "trace_name": name,
                "trace_snapshot": snapshot or {},
                "trace_tags": tags | ({"custom"} if "auto" not in tags else set())
            }
        )
        if not in_progress:
            self.in_progress = False

    def log_info(
            self,
            message: str | None = None,
            snapshot: dict | None = None,
            tags: set[str] | None = None
    ) -> None:
        """This function logs any state."""
        self.log_trace("info", message, snapshot, tags, in_progress=True)

    def log_metric(
            self,
            message: str | None = None,
            snapshot: dict | None = None,
            tags: set[str] | None = None
    ) -> None:
        """This function logs metrics so the snapshot should only contain numbers."""
        self.log_trace("metric", message, snapshot, tags, in_progress=True)

    def log_branch(
            self,
            message: str | None = None,
            snapshot: dict | None = None,
            tags: set[str] | None = None
    ) -> None:
        """This function logs conditional branches."""
        self.log_trace("branch", message, snapshot, tags, in_progress=True)

    def log_end(
            self,
            message: str | None = None,
            snapshot: dict | None = None,
            tags: set[str] | None = None
    ) -> None:
        """This function logs a regular end of an activity."""
        self.log_trace("end", message, snapshot, tags, in_progress=False)

    def log_exit(
            self,
            message: str | None = None,
            snapshot: dict | None = None,
            tags: set[str] | None = None
    ) -> None:
        """This function logs an unusual end of an activity."""
        self.log_trace("exit", message, snapshot, tags, in_progress=False)

    def log_error(
            self,
            message: str | None = None,
            snapshot: dict | None = None,
            tags: set[str] | None = None
    ) -> None:
        """This function logs an error in an activity."""
        self.log_trace("error", message, snapshot, tags, exc_info=True, in_progress=False)
