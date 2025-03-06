from importlib import import_module
from typing import Type, Any, TypeVar


def resolve_class(name: str) -> Type:
    # Parses the path and loads the class dynamically like: wiretap.json.encoders.DateTimeEncoder
    *module_names, class_name = name.split(".")
    return getattr(import_module(".".join(module_names)), class_name)


T = TypeVar('T')


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

    if not obj:
        raise TypeError(f"Cannot parse {obj_type} due to an invalid definition.")

    if not issubclass(type(obj), obj_type):
        raise TypeError(f"Cannot parse {obj_type} due to an unexpected type '{type(obj)}'.")

    return obj
