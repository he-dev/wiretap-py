from typing import Any, TypeVar, Optional

from .json_multi_encoder import JSONMultiEncoder

T = TypeVar('T')


def nth_or_default(source: list[T], index: int) -> Optional[T]:
    return source[index] if index < len(source) else None
