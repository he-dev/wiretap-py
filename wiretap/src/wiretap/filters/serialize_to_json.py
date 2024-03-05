import json
import logging
import traceback
from datetime import datetime
from uuid import UUID


class JSONMultiEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()

        if isinstance(obj, UUID):
            return obj.__str__()

        return super(JSONMultiEncoder, self).default(obj)


class SerializeToJson(logging.Filter):
    def __init__(self):
        super().__init__("serialize_to_json")

    def filter(self, record: logging.LogRecord) -> bool:
        # if hasattr(record, "node"):

        entry = {
            "timestamp": record.timestamp,  # datetime.fromtimestamp(record.created),
            "activity": record.activity,
            "trace": record.trace,
            "elapsed": round(record.elapsed, 3),
            "message": record.msg,
            "snapshot": record.snapshot if hasattr(record, "snapshot") else None,
            "scope": record.node,
            "exception": None
        }

        if record.exc_info:
            exc_cls, exc, exc_tb = record.exc_info
            # format_exception return a list of lines. Join it a single sing or otherwise an array will be logged.
            entry["exception"] = "".join(traceback.format_exception(exc_cls, exc, exc_tb))

        record.__dict__["json"] = json.dumps(entry, sort_keys=False, allow_nan=False, cls=JSONMultiEncoder)

        # the original exception needs to be removed so that the logger doesn't produce non-json entries
        record.exc_info = None
        return True
