import logging

from wiretap.helpers import get_block, get_trace

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {activity} | {type} | {elapsed:0.1f} | {message} | {extra} | {tags}"


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record: logging.LogRecord):
        block = get_block(record)

        if block:
            record.block = block.name
            record.elapsed = block.elapsed.current
            record.indent = self.indent * block.depth

            trace = get_trace(record)
            if trace:
                record.trace = trace.name
                record.message = trace.message
                record.trace_state = trace.state
                record.trace_tags = sorted(trace.tags | block.tags)
            else:
                record.trace = record.levelname.lower()
                record.message = record.msg
                record.trace_state = None
                record.trace_tags = None

        else:
            record.block = record.funcName
            record.elapsed = 0
            record.trace = None
            record.trace_state = None
            record.trace_tags = None
            record.message = record.msg
            record.indent = self.indent

        return super().format(record)
