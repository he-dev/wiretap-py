from __future__ import annotations

import abc
from typing import Any, Protocol, runtime_checkable

from wiretap.meta.logging.formatting import _Forgiving
from wiretap.util.activity_feed import MessageHeaderFeed, MessagePartFeed, get_message_parts


@runtime_checkable
class ComposeMessage(Protocol):
    @abc.abstractmethod
    def __call__(self, state_items: dict[str, Any], *sources: Any) -> str: ...


class ComposeMessageByAppending(ComposeMessage):
    def __init__(self, header: MessagePartFeed = MessageHeaderFeed(), separator: str = "; ") -> None:
        self._header = header
        self._separator = separator

    def __call__(self, state_items: dict[str, Any], *sources: Any) -> str:
        parts: list[str] = []

        def append(part: str | None) -> None:
            if part is not None:
                parts.append(part)

        get_message_parts(self._header, append)
        for item in sources:
            get_message_parts(item, append)

        template = self._separator.join(part for part in parts)
        return template.format_map(_Forgiving(state_items))
