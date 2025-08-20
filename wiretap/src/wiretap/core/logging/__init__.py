from .json_encoders import *
from .json_formatter import JsonFormatter
from .json_modifiers import *
from .text_formatter import TextFormatter


class ExcludeSpanBegin(logging.Filter):
    def filter(self, record: logging.LogRecord):
        event: SpanEvent | None = record.__dict__.get(SpanEvent.KEY, None)
        if event:
            return not (event.state.get("event", None) == "begin_span" and record.levelno < logging.DEBUG)
        return True
