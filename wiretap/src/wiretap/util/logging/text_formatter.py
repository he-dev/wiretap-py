import json
import logging

from wiretap.core.activity_scope import ActivityEvent, ActivityScope
from wiretap.util import trim_path

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {scope}: {trace} | {elapsed:0.3f} sec | {message} | {trace_state}, {trace_tags}"


class TextFormatter(logging.Formatter):
    indent: str = "."

    def format(self, record: logging.LogRecord):

        include_source = logging.getLogger(__name__).isEnabledFor(logging.DEBUG)

        event = record.__dict__.get(ActivityEvent.KEY, None)
        if not event:
            if scope := ActivityScope.peek():
                event = ActivityEvent(scope)

        if event:
            record.scope = event.scope
            record.indent = 1  # self.indent * activity.scope.depth
            record.properties = stringify_deep(event.state)
            record.activity = {
                "trace_id": event.trace_id,
                "span_id": event.span_id,
                "parent_id": event.parent_id,
                "elapsed": round(event.elapsed, 1),
            }
            record.source = {
                "func": event.frame.function if event.frame else record.funcName,
                "file": trim_path(event.frame.filename) if event.frame else trim_path(record.filename),
                "line": event.frame.lineno if event.frame else record.lineno
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
            record.properties = None
            record.activity = None

        return super().format(record)


def stringify_deep(obj: dict) -> dict | str:
    match obj:
        case dict():
            return {k: stringify_deep(v) for k, v in obj.items()}
        case _:
            return str(obj)
