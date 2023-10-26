import dataclasses
import logging
from typing import Any, Optional, Callable

from .parts import Elapsed, Used, TraceNameByCaller
from .types import TraceExtra, ExcInfo, Activity, Logger


class BasicLogger(Logger):

    def __init__(self, activity: Activity):
        self.activity = activity
        self.elapsed = Elapsed()
        self._logger = logging.getLogger(activity.name)

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

        self._logger.log(level=level, msg=message, exc_info=exc_info, extra=vars(trace_extra) | dict(activity=self.activity.name))


class InitialTraceMissing(Exception):
    pass


@dataclasses.dataclass
class InitialTraceLogged:
    """
    This class provides a mechanism to ensure that an initial trace is logged before any other trace is.
    This situation may occur when telemetry's auto_begin=True and the user forgets to call logger.initial.log_begin.
    """
    activity: Activity
    _value = False

    def yes(self):
        self._value = True

    def require(self, trace: str):
        if not self:
            raise InitialTraceMissing(
                f"Cannot trace <{trace}> for the <{self.activity.name}> activity in <{self.activity.file}:{self.activity.line}>. "
                f"You need to log an initial trace first."
            )

    def __bool__(self) -> bool:
        return self._value


class InitialTrace:
    def __init__(self, logger: BasicLogger, initialize: Callable):
        self._logger = logger
        self._initialize = initialize
        self._used = Used()

    def log_begin(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        if self._used:
            return
        source = dict(file=self._logger.activity.file, line=self._logger.activity.line)
        self._logger.log_trace(str(TraceNameByCaller()), message, (details or {}) | dict(source=source), attachment, logging.INFO)
        self._initialize()


class OtherTrace:
    def __init__(self, logger: BasicLogger, require_initial_trace: Callable[[str], None]):
        self._logger = logger
        self._require_initial_trace = require_initial_trace

    def log_info(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._require_initial_trace(str(TraceNameByCaller()))
        self._logger.log_trace(str(TraceNameByCaller()), message, details, attachment, logging.DEBUG)

    def log_item(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._require_initial_trace(str(TraceNameByCaller()))
        self._logger.log_trace(str(TraceNameByCaller()), message, details, attachment, logging.DEBUG)

    def log_skip(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._require_initial_trace(str(TraceNameByCaller()))
        self._logger.log_trace(str(TraceNameByCaller()), message, details, attachment, logging.DEBUG)

    def log_metric(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._require_initial_trace(str(TraceNameByCaller()))
        self._logger.log_trace(str(TraceNameByCaller()), message, details, attachment, logging.DEBUG)


class FinalTrace:
    def __init__(self, logger: BasicLogger, require_initial_trace: Callable[[str], None]):
        self._logger = logger
        self._used = Used()
        self._require_initial_trace = require_initial_trace

    def log_noop(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(str(TraceNameByCaller()), message, details, attachment, logging.INFO, exc_info=None)

    def log_abort(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(str(TraceNameByCaller()), message, details, attachment, logging.WARN, exc_info=None)

    def log_end(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(str(TraceNameByCaller()), message, details, attachment, logging.INFO, exc_info=None)

    def log_error(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None, exc_info: Optional[ExcInfo | bool] = True) -> None:
        self._log_trace(str(TraceNameByCaller()), message, details, attachment, logging.ERROR, exc_info=exc_info)

    def _log_trace(self, name: str, message: Optional[str], details: Optional[dict[str, Any]], attachment: Optional[Any], level: int, exc_info: Optional[ExcInfo | bool]):
        if self._used:
            return
        self._require_initial_trace(name)
        self._logger.log_trace(name, message, details, attachment, level, exc_info=exc_info)


class TraceLogger:
    def __init__(self, logger: BasicLogger):
        self._initial_trace_logged = InitialTraceLogged(logger.activity)
        self.default = logger
        self.initial = InitialTrace(logger, self._initial_trace_logged.yes)
        self.other = OtherTrace(logger, self._initial_trace_logged.require)
        self.final = FinalTrace(logger, self._initial_trace_logged.require)
