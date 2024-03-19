import logging

from wiretap.context import current_activity


class AddCurrentActivity(logging.Filter):
    def __init__(self):
        super().__init__("add_current_activity")

    def filter(self, record: logging.LogRecord) -> bool:
        node = current_activity.get()
        if node:
            record.__dict__["activity_elapsed"] = [round(float(n.value.elapsed), 3) for n in node]
            record.__dict__["activity_id"] = [n.id for n in node]
            record.__dict__["activity_name"] = [n.value.name for n in node]

            # This is a plain record so add default fields.
            if not hasattr(record, "event_name"):
                record.__dict__["event_name"] = f"${record.levelname}"
                record.__dict__["event_snapshot"] = {}
                record.__dict__["event_tags"] = ["plain"]
                record.__dict__["event_message"] = record.msg
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
