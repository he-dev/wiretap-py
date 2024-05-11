import logging

from wiretap.context import current_activity
from wiretap.tools import nth_or_default


class AddCurrentActivity(logging.Filter):
    def __init__(self):
        super().__init__("add_current_activity")

    def filter(self, record: logging.LogRecord) -> bool:
        node = current_activity.get()
        if node:
            record.__dict__["sequence_elapsed"] = [round(float(n.value.elapsed), 3) for n in node]
            record.__dict__["sequence_id"] = [n.id for n in node]
            record.__dict__["sequence_name"] = [n.value.name for n in node]

            record.__dict__["activity_elapsed"] = nth_or_default(record.__dict__["sequence_elapsed"], 0)
            record.__dict__["activity_id"] = nth_or_default(record.__dict__["sequence_id"], 0)
            record.__dict__["activity_name"] = nth_or_default(record.__dict__["sequence_name"], 0)

            # This is a plain record so add default fields.
            if not hasattr(record, "trace_name"):
                record.__dict__["trace_name"] = f":{record.levelname}"
                record.__dict__["trace_snapshot"] = {}
                record.__dict__["trace_tags"] = {"plain"}
                record.__dict__["trace_message"] = record.msg
                record.__dict__["source"] = {
                    "file_path": record.filename,
                    "file_line": record.lineno
                }

            if "source" not in record.__dict__:
                record.__dict__["source"] = {
                    "file_path": node.value.frame.filename,
                    "file_line": node.value.frame.lineno
                }
            record.__dict__["exception"] = None

            if "event.tags" in record.__dict__:
                record.__dict__["event.tags"] = list(record.__dict__["event.tags"])

        return True
