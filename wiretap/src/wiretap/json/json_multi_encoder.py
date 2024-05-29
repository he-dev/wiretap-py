import json
import pathlib
from datetime import datetime
from enum import Enum
from uuid import UUID


class JSONMultiEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()

        if isinstance(obj, UUID):
            return obj.__str__()

        if isinstance(obj, pathlib.Path):
            return obj.as_posix()

        if isinstance(obj, Enum):
            return str(obj)

        if isinstance(obj, set):
            return list(obj)

        return super(JSONMultiEncoder, self).default(obj)
