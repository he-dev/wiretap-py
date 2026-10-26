import itertools
import pathlib
from collections import deque
from enum import Enum
from typing import TypeVar, Optional, Iterable, Generator

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
    _path = pathlib.Path(path)
    try:
        cut_index = _path.parts.index("src")
        return pathlib.Path(*_path.parts[cut_index:]).as_posix()
    except ValueError:
        # core: 'path' is apparently a single name, so return the original one.
        return _path.as_posix()


def flatten_dict_iterative(d: dict, sep: str = '.') -> dict:
    result = {}

    # The stack holds tuples of (prefix_key, dictionary_to_process)
    stack = [('', d)]

    while stack:
        # core: Preserves the original top-to-bottom insertion (FIFO)
        parent_key, current_dict = stack.pop(0)

        for k, v in current_dict.items():
            # Construct the new composite key
            new_key = f"{parent_key}{sep}{k}" if parent_key else k

            if isinstance(v, dict):
                # If it's a dict, push it to the stack to process later
                stack.append((new_key, v))
            else:
                # Otherwise, assign the value to the result dictionary
                result[new_key] = v

    return result


class Missing:
    def __init__(self, path):
        self.path = path

    def __getitem__(self, key):
        return Missing(f"{self.path}[{key}]")

    def __format__(self, spec):
        suffix = f":{spec}" if spec else ""
        return f"{{{self.path}{suffix}}}"


class FormatData(dict):
    def __missing__(self, key):
        return Missing(key)

    def __getitem__(self, key):
        value = super().__getitem__(key)
        if isinstance(value, dict):
            return FormatData(value)
        return value
