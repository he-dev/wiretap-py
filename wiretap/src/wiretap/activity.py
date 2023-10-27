import dataclasses
import logging
from typing import Callable, Any

from .parts import TraceNameByCaller, Elapsed, OneTimeFalse
from .trace import Trace, TraceLite


class Activity:
    def __init__(self, name: str, file: str, line: int):
        self.name = name
        self.file = file
        self.line = line
        self.elapsed = Elapsed()
        self._logger = logging.getLogger(name)
        self._started = ActivityStartLogged(name, file, line)
        self._finalized = OneTimeFalse()

        def _log_start(trace: Trace):
            self._started.yes_for(trace.name)
            self.log(trace.with_details(source=dict(file=self.file, line=self.line)))

        def _log_other(trace: Trace):
            self._started.require_for(trace.name)
            self.log(trace)

        def _log_final(trace: Trace):
            if not self._finalized:
                self._started.require_for(trace.name)
                self.log(trace)

        self.start = StartTrace(_log_start)
        self.other = OtherTrace(_log_other)
        self.final = FinalTrace(_log_final)

    def log(self, trace: Trace) -> None:
        self._logger.log(
            level=trace.level,
            msg=trace.message,
            exc_info=trace.exc_info,
            extra=dict(
                activity=self.name,
                trace=trace.name,
                elapsed=float(self.elapsed),
                details=trace.details,
                attachment=trace.attachment
            )
        )


class StartTrace:
    def __init__(self, log: Callable[[Trace], None]):
        self._log = log

    def trace_begin(self, message: str | None = None) -> Trace:
        return Trace(TraceNameByCaller(), message, self._log).as_info()

    def trace_begin_(self, message: str | None = None, details: dict[str, Any] | None = None, attachment: Any | None = None):
        TraceLite(name=TraceNameByCaller(), message=message, details=details or {}, attachment=attachment, level=logging.INFO, _log=self._log).log()


class OtherTrace:
    def __init__(self, log: Callable[[Trace], None]):
        self._log = log

    def trace_info(self, message: str | None = None) -> Trace:
        return Trace(TraceNameByCaller(), message, self._log).as_debug()

    def trace_item(self, message: str | None = None) -> Trace:
        return Trace(TraceNameByCaller(), message, self._log).as_debug()

    def trace_skip(self, message: str | None = None) -> Trace:
        return Trace(TraceNameByCaller(), message, self._log).as_debug()

    def trace_metric(self, message: str | None = None) -> Trace:
        return Trace(TraceNameByCaller(), message, self._log).as_debug()


class FinalTrace:
    def __init__(self, log: Callable[[Trace], None]):
        self._log = log

    def trace_noop(self, message: str | None = None) -> Trace:
        return Trace(TraceNameByCaller(), message, self._log).as_info()

    def trace_abort(self, message: str | None = None) -> Trace:
        return Trace(TraceNameByCaller(), message, self._log).as_warning()

    def trace_error(self, message: str | None = None) -> Trace:
        return Trace(TraceNameByCaller(), message, self._log).as_warning().with_exc_info(True)

    def trace_end(self, message: str | None = None) -> Trace:
        return Trace(TraceNameByCaller(), message, self._log).as_info()


class ActivityAlreadyStarted(Exception):
    def __init__(self, activity: str, file: str, line: int, trace: str):
        super().__init__(
            f"Cannot trace <{trace}> for the <{activity}> activity in <{file}:{line}>. "
            f"You already did that. Did you mean to disable <auto_begin> in <telemetry>?"
        )


class ActivityStartMissing(Exception):
    def __init__(self, activity: str, file: str, line: int, trace: str):
        super().__init__(
            f"Cannot trace <{trace}> for the <{activity}> activity in <{file}:{line}>. "
            f"You need to log an initial trace first."
        )


@dataclasses.dataclass
class ActivityStartLogged:
    """
    This class provides a mechanism to ensure that an initial trace is logged before any other trace is.
    This situation may occur when telemetry's auto_begin=True and the user forgets to call logger.initial.log_begin.
    """
    name: str
    file: str
    line: int
    _value = False

    def yes_for(self, trace: str):
        if self:
            raise ActivityAlreadyStarted(self.name, self.file, self.line, trace)
        self._value = True

    def require_for(self, trace: str):
        if not self:
            raise ActivityStartMissing(self.name, self.file, self.line, trace)

    def __bool__(self) -> bool:
        return self._value
