import logging
from typing import Any, Optional

from .parts import Elapsed, Used, TraceNameByCaller
from .types import TraceExtra, ExcInfo


class BasicLogger:

    def __init__(self, subject: str, activity: str):
        self.subject = subject
        self.activity = activity
        self.elapsed = Elapsed()
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
        trace_extra = TraceExtra(
            trace=name,
            elapsed=float(self.elapsed),
            details=(details or {}),
            attachment=attachment
        )

        self._logger.log(level=level, msg=message, exc_info=exc_info, extra=vars(trace_extra))


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
