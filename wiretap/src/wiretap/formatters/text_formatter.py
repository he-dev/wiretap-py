import logging

from wiretap import TraceTag
from wiretap.scopes.telemetry_scope import TelemetryItem

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {scope}: {trace} | {elapsed:0.3f} sec | {message} | {trace_state}, {trace_tags}"


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record: logging.LogRecord):
        telemetry = TelemetryItem.from_record_or_scope(record)

        if telemetry and (scope := telemetry.scope):
            record.scope = scope.name
            record.elapsed = scope.elapsed.current
            record.indent = self.indent * scope.depth

            if trace := telemetry.trace:
                record.trace = trace.event
                record.message = trace.message
                record.trace_state = trace.dump
                record.trace_tags = (trace.tags | scope.tags)()
            else:
                record.trace = record.levelname.lower()
                record.message = record.msg
                record.trace_state = None
                record.trace_tags = None

        else:
            record.scope = record.funcName
            record.elapsed = 0
            record.trace = str(None).lower()
            record.trace_state = None
            record.trace_tags = {TraceTag.PLAIN}
            record.message = record.msg
            record.indent = self.indent

        return super().format(record)
