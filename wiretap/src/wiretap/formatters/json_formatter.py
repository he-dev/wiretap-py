import functools
import json
import logging
from json import JSONEncoder

from util.type_factory import parse_type
from wiretap.json import encoders as enc, middleware as mid
from wiretap.json import JSONEncoderDefaultFactory
from wiretap.json.middleware import JSONMiddleware

DEFAULT_ENCODERS = [
    enc.DateTimeEncoder(),
    enc.ChainPathEncoder(),
    enc.PathEncoder(),
    enc.UUIDEncoder(),
    enc.EnumEncoder(),
]

DEFAULT_MIDDLEWARE = [
    mid.TimestampMiddleware(),
    mid.ScopeMiddleware(),
    mid.TraceMiddleware(),
    mid.ExceptionMiddleware()
]


class JSONFormatter(logging.Formatter):

    def __init__(
            self,
            encoders: list[str | dict] | None = None,
            middleware: list[str | dict] | None = None
    ) -> None:
        super().__init__()

        self.encoders = DEFAULT_ENCODERS
        self.middleware = DEFAULT_MIDDLEWARE

        if encoders is not None:
            self.encoders = [parse_type(e, JSONEncoder) for e in encoders]

        if middleware is not None:
            self.middleware = [parse_type(p, JSONMiddleware) for p in middleware]

    def format(self, record: logging.LogRecord):
        # Call each middleware and let them create the entry.
        entry = functools.reduce(lambda e, p: p.emit(record, e), self.middleware, {})

        return json.dumps(
            entry,
            sort_keys=False,
            allow_nan=False,
            default=JSONEncoderDefaultFactory.create_func(self.encoders)
        )
