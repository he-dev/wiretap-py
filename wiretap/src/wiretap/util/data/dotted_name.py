from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, init=False)
class DottedName:
    # util: Dotted strings are parsed on input so callers cannot accidentally create one-part dotted keys.
    parts: tuple[str, ...]

    def __init__(self, *parts: str) -> None:
        object.__setattr__(
            self,
            "parts",
            tuple(piece for part in parts for piece in part.split(".") if piece),
        )

    def append(self, *parts: str) -> Self:
        # util: Append keeps construction explicit; no path-like operator is used for dotted log names.
        return DottedName(*self.parts, *parts)

    def __str__(self) -> str:
        return ".".join(self.parts)

    @property
    def activity(self) -> Self:
        return self.append("activity")

    @property
    def state(self) -> Self:
        return self.append("state")

    @property
    def status(self) -> Self:
        return self.append("status")

    @property
    def name(self) -> Self:
        return self.append("name")

    @property
    def tags(self) -> Self:
        return self.append("tags")

    @property
    def role(self) -> Self:
        return self.append("role")

    @property
    def code(self) -> Self:
        return self.append("code")

    @property
    def depth(self) -> Self:
        return self.append("depth")

    @property
    def path(self) -> Self:
        return self.append("path")

    @property
    def duration_ms(self) -> Self:
        return self.append("duration_ms")

    @property
    def trace_id(self) -> Self:
        return self.append("trace_id")

    @property
    def span_id(self) -> Self:
        return self.append("span_id")

    @property
    def parent_span_id(self) -> Self:
        return self.append("parent_span_id")
