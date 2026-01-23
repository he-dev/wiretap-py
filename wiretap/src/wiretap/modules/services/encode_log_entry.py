from datetime import datetime, date
from enum import Enum
from json import JSONEncoder
from pathlib import Path
from typing import Any
from uuid import UUID

from wiretap.modules.chain_path import ChainPath


class DefaultEncode:
    def __init__(self, encoders: list[JSONEncoder]) -> None:
        self._encoders = encoders
        self._cache: dict[type, JSONEncoder] = {}

    def __call__(self, obj: Any) -> Any | None:
        obj_type = type(obj)

        if cached := self._cache.get(obj_type):
            try:
                return cached.default(obj)
            except TypeError as e:
                raise TypeError(f"Cached encoder {type(cached).__name__} failed for {obj_type.__name__}.") from e

        for encoder in self._encoders:
            try:
                result = encoder.default(obj)
                self._cache[obj_type] = encoder
                return result
            except TypeError:
                pass

        # core: Create a string with all supported encoders.
        supported = ", ".join(type(e).__name__ for e in self._encoders) or "<none>"
        raise TypeError(f"JSON encoding not supported for {obj_type.__name__}. Supported encoders in chain: {supported}.")


class EncodeDateTime(JSONEncoder):
    """Supports: datetime -> ISO 8601 string"""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError


class EncodeUUID(JSONEncoder):
    """Supports: uuid.UUID -> string"""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        raise TypeError


class EncodePath(JSONEncoder):
    """Supports: pathlib.Path -> posix path string"""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Path):
            return obj.as_posix()
        raise TypeError


class EncodeEnum(JSONEncoder):
    """Supports: enum.Enum -> string (via str(enum))"""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Enum):
            return str(obj)
        raise TypeError


class EncodeSet(JSONEncoder):
    """Supports: set -> list"""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, set):
            return list(obj)
        raise TypeError


class EncodeChainPath(JSONEncoder):
    """Supports: ChainPath -> string"""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, ChainPath):
            return str(obj)
        raise TypeError


class EncodeToDict(JSONEncoder):
    """Supports: objects with .to_dict() -> dict-like"""

    def default(self, obj: Any) -> Any:
        to_dict = getattr(obj, "to_dict", None)
        if callable(to_dict):
            return to_dict()
        raise TypeError
