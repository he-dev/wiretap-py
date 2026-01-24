import functools
import json
import logging
from json import JSONEncoder
from typing import Any

from wiretap.util.services.encode_log_entry import DefaultEncode
from wiretap.util.services.mutate_log_entry import MutateLogEntry, LogContext
from wiretap.meta.type_factory import create_instance


class JsonFormatter(logging.Formatter):

    def __init__(
            self,
            encoders: list[str | dict] | None = None,
            properties: list[str | dict] | None = None
    ) -> None:
        super().__init__()

        if encoders is not None:
            self.default_encode = DefaultEncode([create_instance(e, JSONEncoder) for e in encoders])

        if properties is not None:
            self.modifiers = [create_instance(p, MutateLogEntry) for p in properties]

    def format(self, record: logging.LogRecord):
        # core: Apply each modifier.
        entry: dict[str, Any] = functools.reduce(lambda current, modifier: modifier(LogContext(record, current)), self.modifiers, {})

        return json.dumps(
            entry,
            sort_keys=False,
            allow_nan=False,
            default=self.default_encode
        )
