import logging

from ..context import current_activity


class AddIndentExtra(logging.Filter):
    def __init__(self, char: str = "."):
        super().__init__("indent")
        self.char = char

    def filter(self, record: logging.LogRecord) -> bool:
        logger = current_activity.get()
        indent = self.char * (logger.depth or 1) if logger else self.char
        setattr(record, self.name, indent)
        return True
