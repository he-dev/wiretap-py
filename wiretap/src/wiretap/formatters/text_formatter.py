import logging

from wiretap.scopes import logger_scope, logger_trace

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {activity} | {type} | {elapsed:0.1f} | {message} | {extra} | {tags}"


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record: logging.LogRecord):
        scope = logger_scope(record)

        if scope:
            record.scope = scope.name
            record.elapsed = scope.elapsed.current
            record.indent = self.indent * scope.depth

            trace = logger_trace(record)
            if trace:
                record.trace = trace.name
                record.message = trace.message
                record.trace_state = trace.state
                record.trace_tags = sorted(trace.tags | scope.tags)
            else:
                record.trace = record.levelname.lower()
                record.message = record.msg
                record.trace_state = None
                record.trace_tags = None

        else:
            record.scope = record.funcName
            record.elapsed = 0
            record.trace = None
            record.trace_state = None
            record.trace_tags = None
            record.message = record.msg
            record.indent = self.indent

        return super().format(record)
