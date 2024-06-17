import logging

from wiretap import tag
from wiretap.data import WIRETAP_KEY, Entry

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {activity} | {type} | {elapsed:0.1f} | {message} | {extra} | {tags}"


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record):
        if WIRETAP_KEY in record.__dict__:
            entry: Entry = record.__dict__[WIRETAP_KEY]
            record.activity = entry.activity.name
            record.elapsed = round(float(entry.activity.elapsed), 3)
            record.type = entry.trace.type
            record.trace = entry.trace.name
            record.message = entry.trace.message
            record.extra = entry.extra
            record.tags = entry.tags_sorted
            record.indent = self.indent * entry.activity.depth
        else:
            record.activity = record.funcName
            record.elapsed = -1
            record.type = "default"
            record.trace = None
            record.message = record.msg
            record.extra = None
            record.tags = []
            record.indent = self.indent

        return super().format(record)
