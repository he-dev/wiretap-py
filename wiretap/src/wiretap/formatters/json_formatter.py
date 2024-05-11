import json
import logging
from importlib import import_module
from ..tools import JSONMultiEncoder
from wiretap.tools import nth_or_default


class JSONFormatter(logging.Formatter):
    json_encoder_cls: json.JSONEncoder | str | None = JSONMultiEncoder()

    def format(self, record):
        entry = {
            "timestamp": record.timestamp,
            "sequence.elapsed": record.__dict__["sequence_elapsed"],
            "sequence.id": record.__dict__["sequence_id"],
            "sequence.name": record.__dict__["sequence_name"],

            "trace.message": record.__dict__["trace_message"],
            "trace.name": record.__dict__["trace_name"],
            "trace.snapshot": record.__dict__["trace_snapshot"],
            "trace.tags": record.__dict__["trace_tags"],
            "source": record.__dict__["source"],
            "exception": record.exception
        }

        entry["activity.elapsed"] = nth_or_default(entry["sequence.elapsed"], 0)
        entry["activity.depth"] = len(entry["sequence.id"])
        entry["activity.id"] = nth_or_default(entry["sequence.id"], 0)
        entry["activity.name"] = nth_or_default(entry["sequence.name"], 0)

        entry["previous.elapsed"] = nth_or_default(entry["sequence.elapsed"], 1)
        entry["previous.id"] = nth_or_default(entry["sequence.id"], 1)
        entry["previous.name"] = nth_or_default(entry["sequence.name"], 1)

        # Path to JOSONEncoder class is specified, e.g.: json_encoder_cls: wiretap.tools.JSONMultiEncoder
        if isinstance(self.json_encoder_cls, str):
            # parses the path and loads the class it dynamically:
            *module, cls = self.json_encoder_cls.split(".")
            self.json_encoder_cls = getattr(import_module(".".join(module)), cls)

        return json.dumps(entry, sort_keys=False, allow_nan=False, cls=self.json_encoder_cls)
