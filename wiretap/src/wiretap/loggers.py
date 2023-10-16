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
        self._start = timer()
        self._logger = logging.getLogger(f"{subject}.{activity}")

    @property
    def elapsed(self) -> float:
        return timer() - self._start

    def log_trace(
            self,
            name: str,
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None,
            level: int = logging.DEBUG,
            exc_info: Optional[ExcInfo | bool] = None,
            extra: Optional[dict[str, Any]] = None
    ):
        self._logger.setLevel(level)

        trace_extra = TraceExtra(
            trace=name,
            elapsed=self.elapsed,
            details=(details or {}),
            attachment=attachment
        )

        extra = (extra or {}) | vars(trace_extra)

        self._logger.log(level=level, msg=message, exc_info=exc_info, extra=extra)

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
            exc_info: Optional[ExcInfo | bool] = None,
            extra: Optional[dict[str, Any]] = None,
            group: Optional[str] = None
    ):
        pass


class InitialTraceLogger:
    def __init__(self, log_trace: LogTrace):
        self._log_trace = log_trace

    def log_begin(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None, inputs: Optional[dict[str, Any]] = None, inputs_spec: Optional[dict[str, str | Callable | None]] = None) -> None:
        self._log_trace(message, details, attachment, logging.INFO, group="initial", extra=dict(inputs=inputs, inputs_spec=inputs_spec))


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
        self._log_trace(message, details, attachment, logging.INFO, group="final")

    def log_abort(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.INFO, group="final")

    def log_end(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None, output: Optional[T] = None, output_spec: Optional[str | Callable[[T], Any] | None] = None) -> None:
        self._log_trace(message, details, attachment, logging.INFO, group="final", extra=dict(output=output, output_spec=output_spec))

    def log_error(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.ERROR, group="final", exc_info=True)


class TraceLogger(Tracer):
    def __init__(self, logger: BasicLogger):
        self.default = logger
        self.traces: set[str] = set()

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
            exc_info: Optional[ExcInfo | bool] = None,
            extra: Optional[dict[str, Any]] = None,
            group: Optional[str] = None
    ):
        name = inspect.stack()[1][3]
        name = re.sub("^log_", "", name, flags=re.IGNORECASE)

        self.default.log_trace(name, message, details, attachment, level, exc_info, extra)
        if group:
            self.traces.add(group)
