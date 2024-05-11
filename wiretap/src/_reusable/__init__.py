from typing import TypeVar, Optional

from .elapsed import Elapsed
from .node import Node

T = TypeVar('T')


def nth_or_default(source: list[T], index: int) -> Optional[T]:
    return source[index] if index < len(source) else None
