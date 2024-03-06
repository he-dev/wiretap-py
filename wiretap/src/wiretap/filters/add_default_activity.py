import logging

from wiretap.context import current_activity


class AddDefaultActivity(logging.Filter):
    def __init__(self):
        super().__init__("add_default_activity")

    def filter(self, record: logging.LogRecord) -> bool:
        if not current_activity.get():
            record.__dict__["activity"] = record.funcName
            record.__dict__["event"] = f"${record.levelname}"
            record.__dict__["elapsed"] = 0
            record.__dict__["snapshot"] = {}
            record.__dict__["exception"] = None
            record.__dict__["scope"] = dict(
                prev_id=None,
                this_id=None
            )
            record.__dict__["source"] = dict(
                file=record.filename,
                line=record.lineno
            )

        return True
