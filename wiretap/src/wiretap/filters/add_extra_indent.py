import logging

from ..types import current_logger


class AddIndentExtra(logging.Filter):
    def __init__(self, char: str = "."):
        super().__init__("indent")
        self.char = char

    def filter(self, record: logging.LogRecord) -> bool:
        logger = current_logger.get()
        indent = self.char * (logger.depth or 1) if logger else self.char
        setattr(record, self.name, indent)
        return True
