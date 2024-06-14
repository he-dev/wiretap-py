import logging
from typing import Any


class ConstField(logging.Filter):
    def __init__(self, mapping: dict[str, Any]):
        super().__init__()
        self.mapping = mapping

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in self.mapping.items():
            setattr(record, key, value)
        return True
