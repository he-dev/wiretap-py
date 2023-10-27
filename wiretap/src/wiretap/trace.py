import dataclasses
import logging
from typing import Any, Callable

from .types import ExcInfo
from .parts import TraceNameByCaller


class Trace:
    def __init__(self, name: str | TraceNameByCaller, message: str, log: Callable[["Trace"], None] | None):
        self.name = str(name)
        self.message = message
        self.details: dict[str, Any] = {}
        self.attachment: Any | None = None
        self.level: int = logging.INFO
        self.exc_info: ExcInfo | bool | None = None
        self._log = log or (lambda _: None)

    def with_details(self, **kwargs) -> "Trace":
        self.details = self.details | kwargs
        return self

    def with_attachment(self, value: Any) -> "Trace":
        self.attachment = value
        return self

    def with_exc_info(self, value: ExcInfo | bool) -> "Trace":
        self.exc_info = value
        return self

    def with_level(self, value: int) -> "Trace":
        self.level = value
        return self

    def as_debug(self) -> "Trace":
        self.level = logging.DEBUG
        return self

    def as_info(self) -> "Trace":
        self.level = logging.INFO
        return self

    def as_warning(self) -> "Trace":
        self.level = logging.WARNING
        return self

    def as_error(self) -> "Trace":
        self.level = logging.ERROR
        return self

    def log(self):
        self._log(self)


@dataclasses.dataclass(frozen=True, slots=True)
class TraceLite:
    name: str | TraceNameByCaller
    message: str | None
    details: dict[str, Any]
    attachment: Any | None
    level: int = logging.DEBUG
    exc_info: ExcInfo | bool | None = None
    _log: Callable[["TraceLite"], None] = lambda _: None

    def log(self):
        self._log(self)
