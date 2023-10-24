import logging
from typing import cast

from ..types import NodeExtra
from ..session import current_logger


class AddNodeExtra(logging.Filter):
    def __init__(self):
        super().__init__("node")

    def filter(self, record: logging.LogRecord) -> bool:
        node = current_logger.get()
        context_extra = NodeExtra(
            parent_id=node.parent.id if node and node.parent else None,
            unique_id=node.id if node else None
        )
        extra = vars(context_extra)
        for k, v in extra.items():
            record.__dict__[k] = v

        return True
