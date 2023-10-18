import inspect
import logging
import re
import uuid
from timeit import default_timer as timer
from typing import Callable, Any, Protocol, Optional, TypeVar

from .types import Logger, Tracer, TraceExtra, ExcInfo


class BasicLogger(Logger):

    def __init__(self, subject: str, activity: str, parent: Optional[Logger] = None):
        self.id = uuid.uuid4()
        self.subject = subject
        self.activity = activity
        self.parent = parent
        self.depth = parent.depth + 1 if parent else 1  # sum(1 for _ in self)
        self._start: float | None = None
        self._logger = logging.getLogger(f"{subject}.{activity}")

    @property
    def elapsed(self) -> float:
        """Gets the current elapsed time in seconds or 0 if called for the first time."""
        if self._start:
            return timer() - self._start
        else:
            self._start = timer()
            return .0

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
            elapsed=self.elapsed,
            details=(details or {}),
            attachment=attachment
        )

        self._logger.log(level=level, msg=message, exc_info=exc_info, extra=vars(trace_extra))

    def __iter__(self):
        current = self
        while current:
            yield current
            current = current.parent


class LogTrace(Protocol):
    def __call__(
            self,
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None,
            level: int = logging.DEBUG,
            exc_info: Optional[ExcInfo | bool] = None
    ):
        pass


class InitialTraceLogger:
    def __init__(self, log_trace: LogTrace):
        self._log_trace = log_trace

    def log_begin(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.INFO)


class OtherTraceLogger:
    def __init__(self, log_trace: LogTrace):
        self._log_trace = log_trace

    def log_info(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.DEBUG)

    def log_item(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.DEBUG)

    def log_skip(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.DEBUG)

    def log_metric(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.DEBUG)


T = TypeVar("T")


class FinalTraceLogger:
    def __init__(self, log_trace: LogTrace):
        self._log_trace = log_trace

    def log_noop(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details or {} | dict(source="final"), attachment, logging.INFO)

    def log_abort(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details or {} | dict(source="final"), attachment, logging.WARN)

    def log_end(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.INFO)

    def log_error(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details or {} | dict(source="final"), attachment, logging.ERROR, exc_info=True)


class TraceLogger(Tracer):
    def __init__(self, logger: BasicLogger):
        self.default = logger
        self.sources: set[str] = set()

    @property
    def initial(self) -> InitialTraceLogger:
        return InitialTraceLogger(self._log_trace)

    @property
    def other(self) -> OtherTraceLogger:
        return OtherTraceLogger(self._log_trace)

    @property
    def final(self) -> FinalTraceLogger:
        return FinalTraceLogger(self._log_trace)

    def _log_trace(
            self,
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None,
            level: int = logging.DEBUG,
            exc_info: Optional[ExcInfo | bool] = None
    ):
        if self._unique_source_logged((details or {}).pop("source", None)):
            return

        self.default.log_trace(
            TraceLogger._trace_name(),
            message,
            details,
            attachment,
            level,
            exc_info
        )

    def _unique_source_logged(self, source: str) -> bool:
        try:
            return source in self.sources
        finally:
            if source:
                self.sources.add(source)

    @staticmethod
    def _trace_name():
        name = inspect.stack()[2][3]
        return re.sub("^log_", "", name, flags=re.IGNORECASE)
