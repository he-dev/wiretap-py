import json
import logging
from datetime import datetime, date
from typing import Any


class _JsonDateTimeEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, (date, datetime)):
            return o.isoformat()


class SerializeDetailsToJson(logging.Filter):
    def __init__(self):
        super().__init__("serialize_snapshot_to_json")

    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, "snapshot") and record.snapshot:
            record.__dict__["snapshot_json"] = json.dumps(record.snapshot, sort_keys=True, allow_nan=False, cls=_JsonDateTimeEncoder)
        return True
