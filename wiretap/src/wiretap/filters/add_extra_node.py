import logging

# from ..session import current_activity
from ..tracing import current_activity


class AddNodeExtra(logging.Filter):
    def __init__(self):
        super().__init__("node")

    def filter(self, record: logging.LogRecord) -> bool:
        node = current_activity.get()
        extra = dict(
            parent_id=node.parent.id if node and node.parent else None,
            unique_id=node.id if node else None
        )
        for k, v in extra.items():
            record.__dict__[k] = v

        return True
