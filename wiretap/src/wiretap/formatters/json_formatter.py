import json
import logging
from importlib import import_module

from wiretap.json import JSONMultiEncoder


class JSONFormatter(logging.Formatter):
    json_encoder_cls: json.JSONEncoder | str | None = JSONMultiEncoder()
    fields: set[str] = {"$activity"}

    def format(self, record):
        entry = {k.lstrip("$"): v for k, v in record.__dict__.items() if k in self.fields}

        # Path to JOSONEncoder class is specified, e.g.: json_encoder_cls: wiretap.tools.JSONMultiEncoder
        if isinstance(self.json_encoder_cls, str):
            # parses the path and loads the class it dynamically:
            *module, cls = self.json_encoder_cls.split(".")
            self.json_encoder_cls = getattr(import_module(".".join(module)), cls)

        return json.dumps(entry, sort_keys=False, allow_nan=False, cls=self.json_encoder_cls)



