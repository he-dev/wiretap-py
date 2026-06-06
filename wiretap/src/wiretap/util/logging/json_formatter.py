import functools
import json
import logging
from json import JSONEncoder
from typing import Any

from wiretap.util.logging.json_encoding import DefaultEncode
from wiretap.util.logging.json_middleware import JSONMiddleware, JSONMiddlewareContext
from wiretap.meta.type_factory import create_instance


class JSONFormatter(logging.Formatter):

    def __init__(
            self,
            encoders: list[str | dict] | None = None,
            middleware: list[str | dict] | None = None
    ) -> None:
        super().__init__()

        if encoders is not None:
            self.default_encode = DefaultEncode([create_instance(e, JSONEncoder) for e in encoders])

        if middleware is not None:
            self.middleware = [create_instance(p, JSONMiddleware) for p in middleware]

    def format(self, record: logging.LogRecord):
        # core: Apply each modifier.
        # entry: dict[str, Any] = functools.reduce(lambda current, middleware: middleware(JSONMiddlewareContext(record, current)), self.middleware, {})

        entry: dict[str, Any] = {}
        for middleware in self.middleware:
            try:
                entry = middleware(JSONMiddlewareContext(record, entry))
            except Exception as error:
                raise RuntimeError(
                    f"{type(middleware).__name__} failed formatting a record "
                    f"from {record.name} at {record.pathname}:{record.lineno}."
                ) from error

        return json.dumps(
            entry,
            sort_keys=False,
            allow_nan=False,
            default=self.default_encode
        )
