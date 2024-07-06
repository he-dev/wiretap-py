import logging

from wiretap.data import WIRETAP_KEY, Entry

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {activity} | {type} | {elapsed:0.1f} | {message} | {extra} | {tags}"


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record):
        if WIRETAP_KEY in record.__dict__:
            entry: Entry = record.__dict__[WIRETAP_KEY]
            record.procedure = entry.procedure.name
            record.elapsed = entry.procedure.elapsed.current
            record.trace = entry.trace.name
            record.message = entry.trace.message
            record.data = entry.trace.data
            record.tags = sorted(entry.trace.tags)
            record.indent = self.indent * entry.procedure.depth
        else:
            record.procedure = record.funcName
            record.elapsed = -1
            record.trace = None
            record.message = record.msg
            record.data = None
            record.tags = []
            record.indent = self.indent

        return super().format(record)
