import json
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