from importlib import import_module
from typing import Type, Any


def resolve_class(type_name: str) -> Type:
    # Parses the path and loads the class dynamically like: wiretap.json.encoders.DateTimeEncoder
    *module_names, class_name = type_name.split(".")
    return getattr(import_module(".".join(module_names)), class_name)


def create_instance(type_name: str | dict) -> Any:
    """
    Creates an instance of the given type.
    Example: wiretap.util.logging.DateTimeEncoder
    """

    match type_name:
        case str():
            try:
                cls = resolve_class(type_name)
                obj = cls()
            except Exception as e:
                raise TypeError(f"Cannot create instance of '{type_name}'.") from e
        case dict():
            type_key = "()"
            if type_key not in type_name:
                raise KeyError(f"Type key '()' missing for '{type_name}'.")
            class_name = type_name[type_key]
            params = {k: v for k, v in type_name.items() if k != type_key}
            cls = resolve_class(class_name)
            obj = cls(**params)
        case _:
            raise TypeError(f"Cannot create type from '{type(type_name)}'. Only from str or dict.")

    return obj
