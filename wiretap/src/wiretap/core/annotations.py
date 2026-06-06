from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FeedToStateItem:
    # core: When True, the value cascades to all activities down the stack.
    cascade: bool = field(default=False)
    default_value: Any = field(default=None)


@dataclass(frozen=True)
class FeedToMessagePart:
    label: str | None = None
