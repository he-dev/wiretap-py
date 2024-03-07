import json
import logging
from importlib import import_module
from ..tools import JSONMultiEncoder


class JSONFormatter(logging.Formatter):
    json_encoder_cls: json.JSONEncoder | str | None = JSONMultiEncoder()

    def format(self, record):
        entry = {
            "timestamp": record.timestamp,
            "activity": record.activity,
            "event": record.event,
            "elapsed": record.elapsed,
            "message": record.msg,
            "snapshot": record.snapshot,
            "tags": record.tags,
            "context": record.context,
            "source": record.source,
            "exception": record.exception
        }

        if isinstance(self.json_encoder_cls, str):
            *module, cls = self.json_encoder_cls.split(".")
            self.json_encoder_cls = getattr(import_module(".".join(module)), cls)

        return json.dumps(entry, sort_keys=False, allow_nan=False, cls=self.json_encoder_cls)
