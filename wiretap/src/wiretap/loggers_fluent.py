import logging
from typing import Any, Callable, TypeVar, Generic, cast

from .loggers import BasicLogger, InitialTraceLogged
from .parts import Used, TraceNameByCaller
from .types import ExcInfo

_T = TypeVar("_T", bound="FluentTrace")


class TraceArgs:
    details: dict[str, Any] = {}
    attachment: Any | None = None
    level: int = logging.INFO
    exc_info: ExcInfo | bool | None = None


class FluentTrace(Generic[_T]):
    def __init__(self, logger: BasicLogger, child: _T):
        self._logger = logger
        self._child = child
        self._args = TraceArgs()

    def with_details(self, **kwargs) -> _T:
        self._args.details = self._args.details | kwargs
        return self._child

    def with_attachment(self, value: Any) -> _T:
        self._args.attachment = value
        return self._child

    def with_exc_info(self, value: ExcInfo | bool) -> _T:
        self._args.exc_info = value
        return self._child

    def as_debug(self) -> _T:
        self._args.level = logging.DEBUG
        return self._child

    def as_info(self) -> _T:
        self._args.level = logging.INFO
        return self._child

    def as_warning(self) -> _T:
        self._args.level = logging.WARNING
        return self._child

    def as_error(self) -> _T:
        self._args.level = logging.ERROR
        return self._child

    def log_trace(self, name: str, message: str | None = None) -> None:
        source = dict(file=self._logger.activity.file, line=self._logger.activity.line)
        self.with_details(source=source)
        self._logger.log_trace(
            name,
            message,
            level=self._args.level,
            details=self._args.details,
            attachment=self._args.attachment,
            exc_info=self._args.exc_info
        )
        self._args = TraceArgs()


class FluentInitialTrace(FluentTrace["FluentInitialTrace"]):
    def __init__(self, logger: BasicLogger, initialize: Callable):
        super().__init__(logger, self)
        self._initialize = initialize
        self._used = Used()

    def log_begin(self, message: str | None = None) -> None:
        if self._used:
            return
        self.as_info()
        self.log_trace(str(TraceNameByCaller()), message)
        self._initialize()


class FluentOtherTrace(FluentTrace["FluentOtherTrace"]):
    def __init__(self, logger: BasicLogger, require_initial_trace: Callable[[str], None]):
        super().__init__(logger, self)
        self._require_initial_trace = require_initial_trace

    def log_info(self, message: str | None = None) -> None:
        self._require_initial_trace(str(TraceNameByCaller()))
        self.as_debug().log_trace(str(TraceNameByCaller()), message)

    def log_item(self, message: str | None = None) -> None:
        self._require_initial_trace(str(TraceNameByCaller()))
        self.as_debug().log_trace(str(TraceNameByCaller()), message)

    def log_skip(self, message: str | None = None) -> None:
        self._require_initial_trace(str(TraceNameByCaller()))
        self.as_debug()
        self.log_trace(str(TraceNameByCaller()), message)

    def log_metric(self, message: str | None = None) -> None:
        self._require_initial_trace(str(TraceNameByCaller()))
        self.as_debug().log_trace(str(TraceNameByCaller()), message)


class FluentFinalTrace(FluentTrace["FluentFinalTrace"]):
    def __init__(self, logger: BasicLogger, require_initial_trace: Callable[[str], None]):
        super().__init__(logger, self)
        self._used = Used()
        self._require_initial_trace = require_initial_trace

    def log_noop(self, message: str | None = None) -> None:
        self.as_info()._log_trace(str(TraceNameByCaller()), message)

    def log_abort(self, message: str | None = None) -> None:
        self.as_warning()._log_trace(str(TraceNameByCaller()), message)

    def log_end(self, message: str | None = None) -> None:
        self.as_info()._log_trace(str(TraceNameByCaller()), message)

    def log_error(self, message: str | None = None) -> None:
        self.as_error().with_exc_info(True)._log_trace(str(TraceNameByCaller()), message)

    def _log_trace(self, name: str, message: str | None = None):
        if self._used:
            return
        self._require_initial_trace(name)
        self.log_trace(name, message)


class FluentTraceLogger:
    def __init__(self, logger: BasicLogger):
        self._initial_trace_logged = InitialTraceLogged(logger.activity)
        self.default = logger
        self.initial = FluentInitialTrace(logger, self._initial_trace_logged.yes)
        self.other = FluentOtherTrace(logger, self._initial_trace_logged.require)
        self.final = FluentFinalTrace(logger, self._initial_trace_logged.require)
