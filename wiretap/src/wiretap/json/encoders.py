from json import JSONEncoder
from typing import Type, Any, Callable, Protocol, runtime_checkable, cast

import cachetools


@runtime_checkable
class JSONEncoderPro(Protocol):
    # This protocol extends the JSONEncoder
    # by allowing to check whether it supports the type being serialized.
    def supports(self, obj_type: Type) -> bool: ...


class JSONEncoderCache:
    # This class caches the encoder search results so that the loop doesn't run on every log.

    @classmethod
    @cachetools.cached(cache={}, key=lambda c, e, t: t)
    def get_encoder_for(cls, encoders: list[JSONEncoder], obj_type: Type) -> JSONEncoder:
        # print(f"Searching encoder for {obj_type}") # Debugging message to see how often the search is used.

        # Find an encoder that can handle the obj_type or use the default one otherwise.
        for encoder in encoders:
            if isinstance(encoder, JSONEncoderPro):
                if encoder.supports(obj_type):
                    return cast(JSONEncoder, encoder)
        return JSONEncoder()


class JSONEncoderDefaultFactory:
    # This class creates a custom default-func that uses multiple encoders.

    @staticmethod
    def create_func(encoders: list[JSONEncoder]) -> Callable[[Any], Any | None]:
        def _default(obj: Any) -> Any | None:
            return JSONEncoderCache.get_encoder_for(encoders, type(obj)).default(obj)

        return _default


class DateTimeEncoder(JSONEncoder, JSONEncoderPro):
    def supports(self, obj_type: Type) -> bool:
        from datetime import datetime
        return issubclass(obj_type, datetime)

    def default(self, obj) -> Any | None:
        return obj.isoformat()


class FloatEncoder(JSONEncoder, JSONEncoderPro):
    def __init__(self, precision: int = 3):
        super().__init__()
        self.precision = precision

    def supports(self, obj_type: Type) -> bool:
        return issubclass(obj_type, float)

    def default(self, obj) -> Any | None:
        return JSONEncoder().default(round(obj, self.precision))


class UUIDEncoder(JSONEncoder, JSONEncoderPro):
    def supports(self, obj_type: Type) -> bool:
        import uuid
        return issubclass(obj_type, uuid.UUID)

    def default(self, obj) -> Any | None:
        return str(obj)


class PathEncoder(JSONEncoder, JSONEncoderPro):
    def supports(self, obj_type: Type) -> bool:
        import pathlib
        return issubclass(obj_type, pathlib.Path)

    def default(self, obj) -> Any | None:
        return obj.as_posix()


class EnumEncoder(JSONEncoder, JSONEncoderPro):
    def supports(self, obj_type: Type) -> bool:
        from enum import Enum
        return issubclass(obj_type, Enum)

    def default(self, obj) -> Any | None:
        return str(obj)


class SetEncoder(JSONEncoder, JSONEncoderPro):
    def supports(self, obj_type: Type) -> bool:
        return issubclass(obj_type, set)

    def default(self, obj) -> Any | None:
        return list(obj)


class FeedPathEncoder(JSONEncoder, JSONEncoderPro):
    def supports(self, obj_type: Type) -> bool:
        from wiretap.data import LoggerPath
        return issubclass(obj_type, LoggerPath)

    def default(self, obj) -> Any | None:
        return str(obj)
