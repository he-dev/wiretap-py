import functools
import json
import logging
from json import JSONEncoder
from typing import Any

from wiretap.util.logging import json_encoders as enc, json_modifiers as mods
from wiretap.util.logging.json_encoders import JSONEncoderDefaultFactory
from wiretap.util.logging.json_modifiers import JsonModifier, JsonModifierContext
from wiretap.meta.type_factory import parse_type

DEFAULT_ENCODERS = [
    enc.DateTimeEncoder(),
    enc.ChainPathEncoder(),
    enc.PathEncoder(),
    enc.UUIDEncoder(),
    enc.EnumEncoder(),
]

DEFAULT_MODIFIERS = [
    mods.AddTimestamp(),
    mods.AddMessage(),
    mods.AddSpan(),
    mods.AddSource(),
    mods.AddProperties(),
    mods.AddException()
]


class JsonFormatter(logging.Formatter):

    def __init__(
            self,
            encoders: list[str | dict] | None = None,
            properties: list[str | dict] | None = None
    ) -> None:
        super().__init__()

        self.encoders = DEFAULT_ENCODERS
        self.modifiers = DEFAULT_MODIFIERS

        if encoders is not None:
            self.encoders = [parse_type(e, JSONEncoder) for e in encoders]

        if properties is not None:
            self.modifiers = [parse_type(p, JsonModifier) for p in properties]

    def format(self, record: logging.LogRecord):
        # core: Call each modifier.
        # entry = functools.reduce(lambda current, modifier: modifier.apply(record, current), self.modifiers, {})
        entry: dict[str, Any] = functools.reduce(lambda current, modifier: modifier.apply(JsonModifierContext(record, current)), self.modifiers, {})

        return json.dumps(
            entry,
            sort_keys=False,
            allow_nan=False,
            default=JSONEncoderDefaultFactory.create_func(self.encoders)
        )

