import logging
from datetime import datetime, timezone


class AddTimestampExtra(logging.Filter):
    def __init__(self, tz: str = "utc"):
        super().__init__("timestamp")
        match tz.casefold().strip():
            case "utc":
                self.tz = datetime.now(timezone.utc).tzinfo  # timezone.utc
            case "local" | "lt":
                self.tz = datetime.now(timezone.utc).astimezone().tzinfo

    def filter(self, record: logging.LogRecord) -> bool:
        setattr(record, self.name, datetime.fromtimestamp(record.created, tz=self.tz))
        return True
