import logging

from wiretap.data import WIRETAP_KEY, Entry

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {activity} | {type} | {elapsed:0.1f} | {message} | {extra} | {tags}"


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record):
        if WIRETAP_KEY in record.__dict__:
            entry: Entry = record.__dict__[WIRETAP_KEY]
            record.activity = entry.activity.name or entry.activity.func
            record.elapsed = round(float(entry.activity.elapsed), 3)
            record.code = entry.trace.code
            record.trace = entry.trace.name
            record.context = entry.activity.context
            record.message = entry.trace.message
            record.body = entry.body
            record.tags = sorted(entry.tags)
            record.indent = self.indent * entry.activity.depth
        else:
            record.activity = record.funcName
            record.elapsed = -1
            record.code = "default"
            record.trace = None
            record.context = None
            record.message = record.msg
            record.body = None
            record.tags = []
            record.indent = self.indent

        return super().format(record)
