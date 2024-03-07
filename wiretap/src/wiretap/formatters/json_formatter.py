import json
import logging
from datetime import datetime
from uuid import UUID


class JSONMultiEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()

        if isinstance(obj, UUID):
            return obj.__str__()

        if isinstance(obj, set):
            return list(obj)

        return super(JSONMultiEncoder, self).default(obj)


class JSONFormatter(logging.Formatter):
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

        return json.dumps(entry, sort_keys=False, allow_nan=False, cls=JSONMultiEncoder)
