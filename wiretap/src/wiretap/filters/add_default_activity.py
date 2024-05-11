import logging
from pathlib import Path

from wiretap.context import current_activity


class AddDefaultActivity(logging.Filter):
    def __init__(self):
        super().__init__("add_default_activity")

    def filter(self, record: logging.LogRecord) -> bool:
        if not current_activity.get():
            record.__dict__["sequence_id"] = []
            record.__dict__["sequence_elapsed"] = []
            record.__dict__["sequence_name"] = [record.funcName]

            record.__dict__["activity_id"] = None
            record.__dict__["activity_elapsed"] = None
            record.__dict__["activity_name"] = record.funcName

            record.__dict__["trace_message"] = record.msg
            record.__dict__["trace_name"] = f":{record.levelname}"
            record.__dict__["trace_snapshot"] = {}
            record.__dict__["trace_tags"] = {"plain"}
            record.__dict__["source"] = {
                "file_path": record.filename,
                "file_line": record.lineno
            }
            record.__dict__["exception"] = None

        return True
