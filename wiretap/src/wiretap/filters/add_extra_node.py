import logging

from ..context import current_activity


class AddNodeExtra(logging.Filter):
    def __init__(self):
        super().__init__("node")

    def filter(self, record: logging.LogRecord) -> bool:
        node = current_activity.get()
        record.__dict__["node"] = dict(
            prev_id=node.parent.id if node and node.parent else None,
            this_id=node.id if node else None
        )
        return True
