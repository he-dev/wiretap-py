from collections.abc import Mapping
from typing import Any


def merge_properties(*args: Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Merge property mappings in order, with explicit keywords taking precedence."""
    properties: dict[str, Any] = {}
    for arg in args:
        if not isinstance(arg, Mapping):
            raise TypeError("Positional properties must be mappings")
        properties.update(arg)
    properties.update(kwargs)
    return properties
