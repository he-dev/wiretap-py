import dataclasses
import logging
from typing import Callable, Any, Protocol

from ..parts import TraceNameByCaller, Elapsed, OneTimeFalse
from .trace import Trace


class NewTrace(Protocol):
    def __call__(self, name: str | None = None) -> Trace: ...


class Activity:
    def __init__(self, name: str, file: str, line: int):
        self.name = name
        self.file = file
        self.line = line
        self.elapsed = Elapsed()

        self._logger = logging.getLogger(name)
        self._started = ActivityStartLogged(name, file, line)
        self._tracing = PendingTrace(name, file, line)
        self._finalized = OneTimeFalse()

        self.start = StartTrace(self._trace(self._log_start))
        self.other = OtherTrace(self._trace(self._log_other))
        self.final = FinalTrace(self._trace(self._log_final))

    def _log(self, trace: Trace) -> None:
        self._tracing.clear()
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

    def _log_start(self, trace: Trace):
        self._started.yes_for(trace.name)
        self._log(trace.with_details(source=dict(file=self.file, line=self.line)))

    def _log_other(self, trace: Trace):
        self._started.require_for(trace.name)
        self._log(trace)

    def _log_final(self, trace: Trace):
        if self._finalized:
            return
        self._started.require_for(trace.name)
        self._log(trace)

    def _trace(self, log: Callable[[Trace], None]) -> NewTrace:
        def _factory(name: str | None = None) -> Trace:
            name = name or str(TraceNameByCaller(2))
            self._tracing.register(name)
            return Trace(name, log)
        return _factory


class StartTrace:
    def __init__(self, trace: NewTrace):
        self._trace = trace

    def trace(self, name: str) -> Trace:
        return self._trace(name).as_info()

    def trace_begin(self) -> Trace:
        return self._trace().as_info()


class OtherTrace:
    def __init__(self, trace: NewTrace):
        self._trace = trace

    def trace(self, name: str) -> Trace:
        return self._trace(name).as_debug()

    def trace_info(self, message: str) -> Trace:
        return self._trace().with_message(message).as_debug()

    def trace_item(self, name: str, value: Any) -> Trace:
        return self._trace().with_details(**{name: value}).as_debug()

    def trace_skip(self, message: str) -> Trace:
        return self._trace().with_message(message).as_debug()

    def trace_metric(self, name: str, value: Any) -> Trace:
        return self._trace().with_details(**{name: value}).as_debug()


class FinalTrace:
    def __init__(self, trace: NewTrace):
        self._trace = trace

    def trace(self, name: str) -> Trace:
        return self._trace(name).as_info()

    def trace_noop(self, message: str) -> Trace:
        return self._trace().with_message(message).as_info()

    def trace_abort(self, message: str) -> Trace:
        return self._trace().with_message(message).as_warning()

    def trace_error(self, message: str) -> Trace:
        return self._trace().with_message(message).as_error().with_exc_info(True)

    def trace_end(self) -> Trace:
        return self._trace().as_info()


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


class PreviousTraceNotLogged(Exception):
    def __init__(self, activity: str, file: str, line: int, trace: str, previous: str):
        super().__init__(
            f"Cannot create or log trace <{trace}> for the <{activity}> activity in <{file}:{line}>. "
            f"You need to log the previous <{previous}> trace first."
        )


class PendingTrace:
    def __init__(self, activity: str, file: str, line: int):
        self.activity = activity
        self.file = file
        self.line = line
        self.name: str | None = None

    def register(self, name: str):
        if self.name:
            raise PreviousTraceNotLogged(self.activity, self.file, self.line, trace=name, previous=self.name)
        self.name = name

    def clear(self):
        self.name = None
