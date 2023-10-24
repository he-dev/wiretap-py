import logging

from ..types import TraceExtra


class AddTraceExtra(logging.Filter):
    def __init__(self):
        super().__init__("trace")

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "trace"):
            trace_extra = TraceExtra(
                trace="info",
                elapsed=0,
                details={},
                attachment=None
            )
            extra = vars(trace_extra)
            for k, v in extra.items():
                record.__dict__[k] = v

        return True
