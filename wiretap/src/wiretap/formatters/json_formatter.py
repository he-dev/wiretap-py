import functools
import json
import logging
from json import JSONEncoder

from util.type_factory import parse_type
from wiretap.json import encoders as enc, modifiers as mods
from wiretap.json import JSONEncoderDefaultFactory
from wiretap.json.modifiers import JSONModifier

DEFAULT_ENCODERS = [
    enc.DateTimeEncoder(),
    enc.ChainPathEncoder(),
    enc.PathEncoder(),
    enc.UUIDEncoder(),
    enc.EnumEncoder(),
]

DEFAULT_MIDDLEWARE = [
    mods.AddTimestamp(),
    mods.AddMessage(),
    mods.AddActivity(),
    mods.AddSource(),
    mods.AddProperties(),
    mods.AddException()
]


class JSONFormatter(logging.Formatter):

    def __init__(
            self,
            encoders: list[str | dict] | None = None,
            properties: list[str | dict] | None = None
    ) -> None:
        super().__init__()

        self.encoders = DEFAULT_ENCODERS
        self.properties = DEFAULT_MIDDLEWARE

        if encoders is not None:
            self.encoders = [parse_type(e, JSONEncoder) for e in encoders]

        if properties is not None:
            self.properties = [parse_type(p, JSONModifier) for p in properties]

    def format(self, record: logging.LogRecord):
        # Call each middleware and let them create the entry.
        entry = functools.reduce(lambda e, p: p.apply(record, e), self.properties, {})

        return json.dumps(
            entry,
            sort_keys=False,
            allow_nan=False,
            default=JSONEncoderDefaultFactory.create_func(self.encoders)
        )
