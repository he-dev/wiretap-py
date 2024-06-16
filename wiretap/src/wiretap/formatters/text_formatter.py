import logging

from wiretap import tag
from wiretap.data import WIRETAP_KEY, Trace, Entry

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {$activity.name} | {$trace.name} | {$activity.elapsed}s | {trace_message} | {trace_snapshot} | {trace_tags}"


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record):
        if WIRETAP_KEY in record.__dict__:
            bag: Entry = record.__dict__[WIRETAP_KEY]
            record.activity_name = bag.activity.name
            record.activity_elapsed = round(float(bag.activity.elapsed), 3)
            record.trace_name = bag.trace.name
            record.trace_message = bag.trace.message
            record.trace_snapshot = bag.note
            record.trace_tags = bag.tags_sorted
            record.indent = self.indent * bag.activity.depth
        else:
            record.activity_name = record.funcName
            record.activity_elapsed = -1
            record.trace_name = f":{record.levelname}"
            record.trace_message = record.msg
            record.trace_snapshot = None
            record.trace_tags = [tag.PLAIN]
            record.indent = self.indent

        return super().format(record)
