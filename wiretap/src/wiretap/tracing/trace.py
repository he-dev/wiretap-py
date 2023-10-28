import logging
from types import TracebackType
from typing import Any, Callable, Type, TypeAlias

from ..parts import TraceNameByCaller

ExcInfo: TypeAlias = bool | tuple[Type[BaseException], BaseException, TracebackType | None] | tuple[None, None, None] | BaseException | None


class Trace:
    def __init__(self, name: str | None, log: Callable[["Trace"], None] | None):
        self.name = name or str(TraceNameByCaller(2))
        self.message: str | None = None
        self.details: dict[str, Any] = {}
        self.attachment: Any | None = None
        self.level: int = logging.INFO
        self.exc_info: ExcInfo | bool | None = None
        self.extra: dict[str, Any] = {}
        self._log = log or (lambda _: None)

    def with_message(self, value: str | None) -> "Trace":
        self.message = value
        return self

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

    def action(self, func: Callable[["Trace"], "Trace"]) -> "Trace":
        return func(self)

    def log(self):
        self._log(self)
