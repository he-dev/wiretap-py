import inspect
import logging
import re
import uuid
from timeit import default_timer as timer
from typing import Any, Optional

from .types import TraceExtra, ExcInfo, Node


class Elapsed:
    _start: float | None = None

    @property
    def current(self) -> float:
        """Gets the current elapsed time in seconds or 0 if called for the first time."""
        if self._start:
            return timer() - self._start
        else:
            self._start = timer()
            return .0

    def __float__(self):
        return self.current


class BasicLogger(Node):

    def __init__(self, subject: str, activity: str, parent: Optional[Node] = None):
        self.id = uuid.uuid4()
        self.subject = subject
        self.activity = activity
        self.parent = parent
        self.depth = parent.depth + 1 if parent else 1  # sum(1 for _ in self)
        self.elapsed = Elapsed()
        self._start: float | None = None
        self._logger = logging.getLogger(f"{subject}.{activity}")

    def log_trace(
            self,
            name: str,
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None,
            level: int = logging.DEBUG,
            exc_info: Optional[ExcInfo | bool] = None
    ):
        self._logger.setLevel(level)

        trace_extra = TraceExtra(
            trace=name,
            elapsed=float(self.elapsed),
            details=(details or {}),
            attachment=attachment
        )

        self._logger.log(level=level, msg=message, exc_info=exc_info, extra=vars(trace_extra))

    def __iter__(self):
        current = self
        while current:
            yield current
            current = current.parent


class Used:
    state = False

    def __bool__(self):
        try:
            return self.state
        finally:
            self.state = True


class TraceNameByCaller:

    def __init__(self):
        caller = inspect.stack()[1][3]
        self.value = re.sub("^log_", "", caller, flags=re.IGNORECASE)

    def __str__(self):
        return self.value


class InitialTrace:
    def __init__(self, logger: BasicLogger):
        self._logger = logger
        self._used = Used()

    def log_begin(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        if self._used:
            return
        self._logger.log_trace(str(TraceNameByCaller()), message, details, attachment, logging.INFO)


class OtherTrace:
    def __init__(self, logger: BasicLogger):
        self._logger = logger

    def log_info(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._logger.log_trace(str(TraceNameByCaller()), message, details, attachment, logging.DEBUG)

    def log_item(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._logger.log_trace(str(TraceNameByCaller()), message, details, attachment, logging.DEBUG)

    def log_skip(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._logger.log_trace(str(TraceNameByCaller()), message, details, attachment, logging.DEBUG)

    def log_metric(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._logger.log_trace(str(TraceNameByCaller()), message, details, attachment, logging.DEBUG)


class FinalTrace:
    def __init__(self, logger: BasicLogger):
        self._logger = logger
        self._used = Used()

    def log_noop(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        if self._used:
            return
        self._logger.log_trace(str(TraceNameByCaller()), message, details, attachment, logging.INFO)

    def log_abort(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        if self._used:
            return
        self._logger.log_trace(str(TraceNameByCaller()), message, details, attachment, logging.WARN)

    def log_end(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        if self._used:
            return
        self._logger.log_trace(str(TraceNameByCaller()), message, details, attachment, logging.INFO)

    def log_error(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        if self._used:
            return
        self._logger.log_trace(str(TraceNameByCaller()), message, details, attachment, logging.ERROR, exc_info=True)


class TraceLogger:
    def __init__(self, logger: BasicLogger):
        self.default = logger
        self.initial = InitialTrace(logger)
        self.other = OtherTrace(logger)
        self.final = FinalTrace(logger)
