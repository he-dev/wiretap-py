import itertools
from collections import deque
from enum import Enum
from importlib import import_module
from typing import TypeVar, Optional, Iterable, Type, Any, Generator

from .elapsed import Elapsed
from .welford import Welford

T = TypeVar('T')


def nth_or_default_(source: list[T], index: int) -> Optional[T]:
    return source[index] if index < len(source) else None


def nth_or_default(source: Iterable[T], index: int, default: Optional[T] = None) -> Optional[T]:
    return next(itertools.islice(source, index, None), default)


def resolve_class(name: str) -> Type:
    # Parses the path and loads the class it dynamically.
    *module_names, class_name = name.split(".")
    return getattr(import_module(".".join(module_names)), class_name)


def map_to_str(values: Iterable[Any] | None) -> set[str]:
    return set(map(lambda x: str(x), values)) if values else set()


def fast_reverse(iterable: Iterable[T]) -> Generator[T, None, None]:
    stack = deque(iterable, maxlen=None)
    while stack:
        yield stack.pop()


class LowerEnum(Enum):
    def __str__(self):
        return self.name.lower()

    def __repr__(self):
        return str(self)


class KebabEnum(Enum):
    def __str__(self):
        return self.name.lower().replace('_', '-').lower()

    def __repr__(self):
        return str(self)
