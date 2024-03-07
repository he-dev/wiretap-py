import logging
from pathlib import Path

from wiretap.context import current_activity


class AddCurrentActivity(logging.Filter):
    def __init__(self):
        super().__init__("add_current_activity")

    def filter(self, record: logging.LogRecord) -> bool:
        node = current_activity.get()
        if node:
            record.__dict__["activity"] = node.value.name

            # This is a plain record so add default fields.
            if not hasattr(record, "event"):
                record.__dict__["event"] = f"${record.levelname}"
                record.__dict__["source"] = dict(
                    file=Path(record.filename).name,
                    line=record.lineno
                )
                record.__dict__["snapshot"] = {}
                record.__dict__["tags"] = ["plain"]

            record.__dict__["elapsed"] = round(float(node.value.elapsed), 3)
            if "source" not in record.__dict__:
                record.__dict__["source"] = dict(
                    file=Path(node.value.frame.filename).name,
                    line=node.value.frame.lineno
                )
            record.__dict__["exception"] = None
            record.__dict__["context"] = dict(
                prev_id=node.parent.id if node.parent else None,
                this_id=node.id
            )

            if isinstance(record.tags, set):
                record.__dict__["tags"] = list(record.tags)

        return True
