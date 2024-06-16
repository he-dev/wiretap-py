import logging

from wiretap import tag
from wiretap.data import WIRETAP_KEY, Trace, Entry

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {$activity.name} | {$trace.name} | {$activity.elapsed}s | {trace_message} | {trace_snapshot} | {trace_tags}"


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record):
        if WIRETAP_KEY in record.__dict__:
            entry: Entry = record.__dict__[WIRETAP_KEY]
            record.activity = entry.activity.name
            record.elapsed = round(float(entry.activity.elapsed), 3)
            record.trace = entry.trace.name
            record.message = entry.trace.message
            record.note = entry.note
            record.tags = entry.tags_sorted
            record.indent = self.indent * entry.activity.depth
        else:
            record.activity = record.funcName
            record.elapsed = -1
            record.trace = f":{record.levelname}"
            record.message = record.msg
            record.note = None
            record.tags = [tag.PLAIN]
            record.indent = self.indent

        return super().format(record)
