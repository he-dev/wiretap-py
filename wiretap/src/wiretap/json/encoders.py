import functools
import json
import pathlib
import uuid
from datetime import datetime
from enum import Enum
from typing import Type

from _reusable import resolve_class


class JSONMultiEncoder(json.JSONEncoder):

    def __init__(self, **kwargs):
        encoders = kwargs.pop('encoders', [])  # The default encoder doesn't support this name.
        super().__init__(**kwargs)
        temp = [resolve_class(e)() for e in encoders]  # Create encoders.
        # Map encoders to a dictionary for faster lookup.
        self.encoders = functools.reduce(lambda d, e: d | {t: e for t in e.types}, temp, {})

    def default(self, obj):
        if isinstance(obj, Enum):
            return str(obj)

        # Use an encoder that can handle the type of obj or the default one.
        encoder: json.JSONEncoder = self.encoders.get(type(obj), super(JSONMultiEncoder, self))
        return encoder.default(obj)


class DateTimeEncoder(json.JSONEncoder):
    types: set[Type] = {datetime}

    def default(self, obj):
        return obj.isoformat()


class UUIDEncoder(json.JSONEncoder):
    types: set[Type] = {uuid.UUID}

    def default(self, obj):
        return obj.__str__()


class PathEncoder(json.JSONEncoder):
    types: set[Type] = {pathlib.Path}

    def default(self, obj):
        return obj.as_posix()


class EnumEncoder(json.JSONEncoder):
    types: set[Type] = {Enum}

    def default(self, obj):
        return str(obj)


class SetEncoder(json.JSONEncoder):
    types: set[Type] = {set}

    def default(self, obj):
        return list(obj)
