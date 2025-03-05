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
    # Parses the path and loads the class dynamically like: wiretap.json.encoders.DateTimeEncoder
    *module_names, class_name = name.split(".")
    return getattr(import_module(".".join(module_names)), class_name)


def parse_type(item: Any, obj_type: Type[T]) -> T:
    # Parses a type from string: wiretap.json.encoders.DateTimeEncoder.
    # Supports parameters as its dictionary.
    obj: T | None = None
    match item:
        case str():
            obj = resolve_class(item)()
        case dict():
            type_key = "()"
            if type_key not in item:
                raise KeyError(f"Type key '()' missing for '{item}'.")
            class_name = item[type_key]
            params = {k: v for k, v in item.items() if k != type_key}
            obj = resolve_class(class_name)(**params)
        case _:
            raise TypeError(f"Cannot parse {obj_type} due to an invalid definition.")

    if not issubclass(type(obj), obj_type):
        raise TypeError(f"Cannot parse {obj_type} due to an unexpected type '{type(obj)}'.")

    return obj


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
