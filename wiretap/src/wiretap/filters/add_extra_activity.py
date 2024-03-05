import logging

from wiretap.context import current_activity


class AddActivityExtra(logging.Filter):
    def __init__(self):
        super().__init__("activity")

    def filter(self, record: logging.LogRecord) -> bool:
        node = current_activity.get()
        if node:
            record.__dict__[self.name] = node.value.name
        else:
            # This is true when the classic logging is used without a valid scope.
            if not hasattr(record, self.name):
                record.__dict__[self.name] = record.funcName

        return True
