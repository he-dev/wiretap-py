import logging

from wiretap.helpers import unpack

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {activity} | {type} | {elapsed:0.1f} | {message} | {extra} | {tags}"


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record):
        procedure, trace = unpack(record)

        if procedure:
            record.procedure = procedure.name
            record.procedure_data = procedure.data
            record.procedure_tags = sorted(procedure.tags)
            record.elapsed = procedure.elapsed.current
            record.indent = self.indent * procedure.depth

            if trace:
                record.trace = trace.name
                record.message = trace.message
                record.trace_data = trace.data
                record.trace_tags = sorted(trace.tags)
            else:
                record.trace = record.funcName
                record.message = record.msg
                record.trace_data = None
                record.trace_tags = None

        else:
            record.procedure = record.funcName
            record.procedure_data = None
            record.procedure_tags = None
            record.elapsed = 0
            record.trace = None
            record.trace_data = None
            record.trace_tags = None
            record.message = record.msg
            record.indent = self.indent

        return super().format(record)
