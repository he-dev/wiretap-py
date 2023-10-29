import contextlib
import dataclasses
import inspect
import logging
import re
from contextvars import ContextVar
from pathlib import Path
from typing import Callable, Any, Protocol, Iterator

from ..tools import Elapsed, Node
from .trace import Trace


class NewTrace(Protocol):
    def __call__(self, name: str | None = None) -> Trace: ...


OnError = Callable[[BaseException, "Activity"], None]
OnBegin = Callable[[Trace], Trace]

current_activity: ContextVar[Node["Activity"] | None] = ContextVar("current_activity", default=None)


class Activity:
    """
    This class represents an activity for which telemetry is collected.
    """

    def __init__(
            self,
            name: str,
            file: str,
            line: int,
            auto_begin: bool = True,
            on_begin: OnBegin | None = None,
            on_error: OnError | None = None
    ):
        self.name = name
        self.file = file
        self.line = line
        self.elapsed = Elapsed()

        self._auto_begin = auto_begin
        self._on_begin = on_begin or (lambda _t: _t)
        self._on_error = on_error or (lambda _exc, _logger: None)
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

    def __enter__(self) -> "Activity":
        parent = current_activity.get()
        self._token = current_activity.set(Node(self, parent))
        if self._auto_begin:
            self.start.trace_begin().action(self._on_begin).log()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            if isinstance(exc_val, (ActivityStartMissing, ActivityAlreadyStarted, PreviousTraceNotLogged)):
                # Do nothing when these errors occur, otherwise the same exception will raise for the default handler.
                pass
            else:
                self._on_error(exc_val, self)
                self.final.trace_error(f"Unhandled <{exc_type.__name__}> has occurred: <{str(exc_val) or 'N/A'}>").log()

        current_activity.reset(self._token)
        return False


@contextlib.contextmanager
def begin_activity(
        name: str,
        auto_begin=True,
        on_begin: OnBegin | None = None,
        on_error: OnError | None = None
) -> Iterator[Activity]:
    stack = inspect.stack()
    frame = stack[2]
    with Activity(
            name=name,
            file=Path(frame.filename).name,
            line=frame.lineno,
            auto_begin=auto_begin,
            on_begin=on_begin,
            on_error=on_error
    ) as activity:
        yield activity
        activity.final.trace_end().log()


@dataclasses.dataclass(frozen=True, slots=True)
class LogAbortWhen(OnError):
    exceptions: type[BaseException] | tuple[type[BaseException], ...]

    def __call__(self, exc: BaseException, activity: Activity) -> None:
        if isinstance(exc, self.exceptions):
            activity.final.trace_abort(f"Unable to complete due to <{type(exc).__name__}>: {str(exc) or '<N/A>'}").log()


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


class OneTimeFalse:
    state = False

    def __bool__(self):
        try:
            return self.state
        finally:
            self.state = True


class TraceNameByCaller:

    def __init__(self, frame_index: int):
        caller = inspect.stack()[frame_index].function
        self.value = re.sub("^trace_", "", caller, flags=re.IGNORECASE)

    def __str__(self):
        return self.value


class ActivityAlreadyStarted(Exception):
    def __init__(self, activity: str, file: str, line: int, trace: str):
        super().__init__(
            f"Cannot trace <{trace}> for the <{activity}> activity in <{file}:{line}>. "
            f"You already did that. Did you mean to disable <auto_begin>?"
        )


class ActivityStartMissing(Exception):
    def __init__(self, activity: str, file: str, line: int, trace: str):
        super().__init__(
            f"Cannot trace <{trace}> for the <{activity}> activity in <{file}:{line}>. "
            f"You need to log an start trace first."
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
    """
    This class helps to make sure that pending traces are logged before the next one.
    """

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
