import logging


class AddActivityExtra(logging.Filter):
    def __init__(self):
        super().__init__("activity")

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, self.name):
            record.__dict__[self.name] = record.funcName

        return True
