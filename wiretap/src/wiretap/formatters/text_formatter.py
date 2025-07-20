import logging

from util import trim_path
from wiretap.scopes.activity_scope import ActivityEvent

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {scope}: {trace} | {elapsed:0.3f} sec | {message} | {trace_state}, {trace_tags}"


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record: logging.LogRecord):

        include_source = logging.getLogger(__name__).isEnabledFor(logging.DEBUG)

        if event := ActivityEvent.extract_or_default(record):
            record.scope = event.scope
            record.indent = 1  # self.indent * activity.scope.depth
            record.context = event.state
            record.activity = {
                "trace_id": event.trace_id,
                "span_id": event.span_id,
                "parent_id": event.parent_id,
                "elapsed": round(event.elapsed, 1),
            }
            record.source = {
                "func": event.frame.function,
                "file": trim_path(event.frame.filename),
                "line": event.frame.lineno
            } if include_source else "off"

        else:
            record.scope = record.funcName
            record.message = record.msg
            record.indent = self.indent
            record.source = {
                "func": record.funcName,
                "file": trim_path(record.filename),
                "line": record.lineno
            } if include_source else "off"
            record.context = None
            record.activity = None

        return super().format(record)
