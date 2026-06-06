from typing import Any, Protocol, runtime_checkable

from wiretap.meta.logging.formatting import _Forgiving
from wiretap.util.activity_feed import PushItemOptions, get_message_parts


@runtime_checkable
class ComposeMessage(Protocol):
    def __call__(self, context: dict[str, Any], *feeds: Any) -> str: ...


class ComposeMessageByAppending(ComposeMessage):
    def __init__(self, separator: str = "; ") -> None:
        self._separator = separator

    def __call__(self, context: dict[str, Any], *feeds: Any) -> str:
        parts: list[str] = []

        def append(label: str, value: Any, options: PushItemOptions | None = None) -> None:
            if value is None:
                return
            text = str(value)
            options = options or {}
            if options.get("label", True) is False:
                parts.append(text)
                return

            separator = options.get("separator", ": ")
            if separator is None:
                separator = ""
            parts.append(f"{label}{separator}{text}")

        for feed in feeds:
            get_message_parts(feed, append)

        template = self._separator.join(part for part in parts)
        return template.format_map(_Forgiving(context))
