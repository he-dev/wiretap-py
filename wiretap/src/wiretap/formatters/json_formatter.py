import json
import logging
from importlib import import_module
from ..tools import JSONMultiEncoder


class JSONFormatter(logging.Formatter):
    json_encoder_cls: json.JSONEncoder | str | None = JSONMultiEncoder()

    def format(self, record):
        entry = {
            "timestamp": record.timestamp,
            "activity.path.elapsed": record.__dict__["activity_elapsed"],
            "activity.path.id": record.__dict__["activity_id"],
            "activity.path.name": record.__dict__["activity_name"],

            "event.message": record.__dict__["event_message"],
            "event.name": record.__dict__["event_name"],
            "event.snapshot": record.__dict__["event_snapshot"],
            "event.tags": record.__dict__["event_tags"],
            "source": record.__dict__["source"],
            "exception": record.exception
        }

        entry["activity.elapsed"] = entry["activity.path.elapsed"][0:0 + 1]
        entry["activity.depth"] = len(entry["activity.id"])
        entry["activity.id"] = entry["activity.path.id"][0:0 + 1]
        entry["activity.name"] = entry["activity.path.name"][0:0 + 1]

        entry["activity.previous.elapsed"] = entry["activity.path.elapsed"][1:1 + 1]
        entry["activity.previous.id"] = entry["activity.path.id"][1:1 + 1]
        entry["activity.previous.name"] = entry["activity.path.name"][1:1 + 1]

        if isinstance(self.json_encoder_cls, str):
            *module, cls = self.json_encoder_cls.split(".")
            self.json_encoder_cls = getattr(import_module(".".join(module)), cls)

        return json.dumps(entry, sort_keys=False, allow_nan=False, cls=self.json_encoder_cls)
