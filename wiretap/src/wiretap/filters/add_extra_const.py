import logging
from typing import Any


class AddConstExtra(logging.Filter):
    def __init__(self, name: str, value: Any):
        self.value = value
        super().__init__(name)

    def filter(self, record: logging.LogRecord) -> bool:
        setattr(record, self.name, self.value)
        return True
