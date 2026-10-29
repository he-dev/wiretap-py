import json
import logging
from json import JSONEncoder
from typing import Any

from wiretap.meta.create_instance import create_instance
from wiretap.util.encoding.encode_json import DefaultEncode
from wiretap.util.buzz.build_json import BuildJSON


class JsonFormatter(logging.Formatter):

    def __init__(
            self,
            encoders: list[str | dict] | None = None,
            pipeline: list[str | dict] | None = None
    ) -> None:
        super().__init__()

        if encoders is not None:
            encoder_instances: list[JSONEncoder] = []
            for definition in encoders:
                encoder = create_instance(definition)
                if not isinstance(encoder, JSONEncoder):
                    raise TypeError(f"Expected JSONEncoder, got {type(encoder).__name__}.")
                encoder_instances.append(encoder)
            self.default_encode = DefaultEncode(encoder_instances)

        self.builders: list[BuildJSON] = []
        for definition in pipeline or []:
            builder = create_instance(definition)
            if not isinstance(builder, BuildJSON):
                raise TypeError(f"Expected BuildJSON, got {type(builder).__name__}.")
            self.builders.append(builder)

        # core: Collect all root keys from the builders keeping their order.
        self.root_keys = tuple(dict.fromkeys(
            key
            for builder in self.builders
            for key in builder.root_keys
        ))
        self.root_keys = tuple(dict.fromkeys((*self.root_keys, "fixme")))

    def format(self, record: logging.LogRecord):
        # core: Apply each modifier.
        entry: dict[str, Any] = dict.fromkeys(self.root_keys)
        # core: Copy record diagnostics so builders can add fixme without modifying the record.
        entry["fixme"] = list(record.__dict__.get("fixme") or [])
        for build in self.builders:
            entry = build(record, entry)

        # core: Remove the "fixme" key to avoid empty lists or "false positives".
        if entry.get("fixme") == []:
            del entry["fixme"]

        return json.dumps(
            entry,
            sort_keys=False,
            allow_nan=False,
            default=self.default_encode
        )
