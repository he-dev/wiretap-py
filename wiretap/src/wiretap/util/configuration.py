from __future__ import annotations

import logging
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from types import TracebackType
from typing import ClassVar, Self

from wiretap.util.activity_message import ComposeMessage, ComposeMessageByAppending


@dataclass
class Configuration:
    # core: Runtime behavior shared by all nested wiretap scopes.
    compose_message: ComposeMessage = field(default_factory=ComposeMessageByAppending)
    internal_logger: logging.Logger = field(default_factory=lambda: logging.getLogger("wiretap"))
    attach_trace_context: bool = True

    _current: ClassVar[ContextVar[Configuration]]
    _tokens: list[Token[Configuration]] = field(default_factory=list, init=False, repr=False, compare=False)

    @classmethod
    def current(cls) -> Configuration:
        return cls._current.get()

    def __enter__(self) -> Self:
        # meta: Nested configuration scopes restore the previous runtime settings on exit.
        self._tokens.append(self._current.set(self))
        return self

    def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None
    ) -> None:
        if self._tokens:
            self._current.reset(self._tokens.pop())


Configuration._current = ContextVar("wiretap_configuration", default=Configuration())
