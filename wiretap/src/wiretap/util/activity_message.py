import abc
from typing import Any, Protocol, runtime_checkable

from wiretap.meta.logging.formatting import _Forgiving
from wiretap.util.activity_feed import MessageHeaderFeed, MessagePartFeed, get_message_parts


@runtime_checkable
class ComposeMessage(Protocol):
    @abc.abstractmethod
    def __call__(self, context: dict[str, Any], *feeds: Any) -> str: ...


class ComposeMessageByAppending(ComposeMessage):
    def __init__(self, header: MessagePartFeed = MessageHeaderFeed(), separator: str = "; ") -> None:
        self._header = header
        self._separator = separator

    def __call__(self, context: dict[str, Any], *feeds: Any) -> str:
        parts: list[str] = []

        def append(label: str | None, value: Any) -> None:
            if value is None:
                return
            text = str(value)
            parts.append(f"{label}: {text}" if label else text)

        for feed in (self._header, *feeds):
            get_message_parts(feed, append)

        template = self._separator.join(part for part in parts)
        return template.format_map(_Forgiving(context))
