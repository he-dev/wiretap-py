import json
import logging
from json import JSONEncoder
from typing import Any

from wiretap.meta.type_factory import create_instance
from wiretap.util.encoding.encode_json import DefaultEncode
from wiretap.util.buzz.build_json import BuildJSON


class JsonFormatter(logging.Formatter):

    def __init__(
            self,
            encoders: list[str | dict] | None = None,
            properties: list[str | dict] | None = None
    ) -> None:
        super().__init__()

        if encoders is not None:
            self.default_encode = DefaultEncode([create_instance(e, JSONEncoder) for e in encoders])

        self.builders = [create_instance(p, BuildJSON) for p in (properties or [])]
        # core: Collect all root keys from the builders keeping their order.
        self.root_keys = tuple(dict.fromkeys(
            key
            for builder in self.builders
            for key in builder.root_keys
        ))
        self.root_keys = tuple(dict.fromkeys((*self.root_keys, "@errors")))

    def format(self, record: logging.LogRecord):
        # core: Apply each modifier.
        entry: dict[str, Any] = dict.fromkeys(self.root_keys)
        entry["@errors"] = []
        for build in self.builders:
            entry = build(record, entry)

        # core: Remove the "@errors" key to avoid empty lists or "false positives".
        if entry.get("@errors") == []:
            del entry["@errors"]

        return json.dumps(
            entry,
            sort_keys=False,
            allow_nan=False,
            default=self.default_encode
        )
