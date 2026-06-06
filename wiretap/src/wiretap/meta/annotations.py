from __future__ import annotations

from functools import cache
from typing import Any, get_type_hints


# core: Reads and caches annotated fields for status classes because they use [Annotated] fields.
@cache
def _annotated_fields(cls: type) -> dict[type, dict[str, Any]]:
    # note: The index structure is: {channel_type: {field_name: annotation}} resolved once per class.
    index: dict[type, dict[str, Any]] = {}
    hints = get_type_hints(cls, include_extras=True)
    for name, hint in hints.items():
        for annotation in getattr(hint, "__metadata__", ()):
            index.setdefault(type(annotation), {})[name] = annotation
    return index
