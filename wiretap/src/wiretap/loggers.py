import dataclasses
import logging
from typing import Any, Optional, Callable, TypeVar, Generic

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
