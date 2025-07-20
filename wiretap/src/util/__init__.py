import itertools
import pathlib
from collections import deque
from enum import Enum
from importlib import import_module
from typing import TypeVar, Optional, Iterable, Type, Any, Generator

from .elapsed import Elapsed

T = TypeVar('T')


def nth_or_default_(source: list[T], index: int) -> Optional[T]:
    return source[index] if index < len(source) else None


def nth_or_default(source: Iterable[T], index: int, default: Optional[T] = None) -> Optional[T]:
    return next(itertools.islice(source, index, None), default)


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
    """ Converts a snake_case string to a kebab-case string. """

    def __str__(self):
        return self.name.lower().replace('_', '-').lower()

    def __repr__(self):
        return str(self)


def trim_path(path: str) -> str:
    # core: Get rid of the unimportant part.
    path = pathlib.Path(path)
    try:
        cut_index = path.parts.index("src")
        return pathlib.Path(*path.parts[cut_index:]).as_posix()
    except ValueError:
        # core: 'path' is apparently a single name, so return the original one.
        return path.as_posix()

