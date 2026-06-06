from datetime import datetime, date
from enum import Enum
from functools import cache
from json import JSONEncoder
from pathlib import Path
from typing import Any
from uuid import UUID

from wiretap.util.path_of import PathOf


class DefaultEncode:
    def __init__(self, encoders: list[JSONEncoder]) -> None:
        self._encoders = encoders

    def __call__(self, obj: Any) -> Any | None:
        if encoder := self.encoder_for(type(obj)):  # type: ignore[arg-type]
            return encoder.default(obj)

        for encoder in self._encoders:
            if isinstance(encoder, EncodeType):
                continue
            try:
                return encoder.default(obj)
            except TypeError:
                pass

        return str(obj)

    @cache
    def encoder_for(self, obj_type: type) -> JSONEncoder | None:
        for encoder in self._encoders:
            if isinstance(encoder, EncodeType) and encoder.supports(obj_type):
                return encoder

        return None


class EncodeType(JSONEncoder):
    supported_types: tuple[type, ...] = ()

    @classmethod
    def supports(cls, obj_type: type) -> bool:
        return issubclass(obj_type, cls.supported_types)


class EncodeDateTime(EncodeType):
    """Supports: datetime -> ISO 8601 string"""
    supported_types = (datetime, date)

    def default(self, obj: Any) -> Any:
        if isinstance(obj, self.supported_types):
            return obj.isoformat()
        raise TypeError


class EncodeUUID(EncodeType):
    """Supports: uuid.UUID -> string"""
    supported_types = (UUID,)

    def default(self, obj: Any) -> Any:
        if isinstance(obj, self.supported_types):
            return str(obj)
        raise TypeError


class EncodePath(EncodeType):
    """Supports: pathlib.Path -> posix path string"""
    supported_types = (Path,)

    def default(self, obj: Any) -> Any:
        if isinstance(obj, self.supported_types):
            return obj.as_posix()
        raise TypeError


class EncodeEnum(EncodeType):
    """Supports: enum.Enum -> string (via str(enum))"""
    supported_types = (Enum,)

    def default(self, obj: Any) -> Any:
        if isinstance(obj, self.supported_types):
            return obj.value
        raise TypeError


class EncodeSet(EncodeType):
    """Supports: set -> list"""
    supported_types = (set,)

    def default(self, obj: Any) -> Any:
        if isinstance(obj, self.supported_types):
            return list(obj)
        raise TypeError


class EncodePathOf(EncodeType):
    """Supports: ChainPath -> string"""
    supported_types = (PathOf,)

    def default(self, obj: Any) -> Any:
        if isinstance(obj, self.supported_types):
            return str(obj)
        raise TypeError


class EncodeToDict(JSONEncoder):
    """Supports: objects with .to_dict() -> dict-like"""

    def default(self, obj: Any) -> Any:
        to_dict = getattr(obj, "to_dict", None)
        if callable(to_dict):
            return to_dict()
        raise TypeError
