import logging

from ..types import current_logger, TraceExtra


class AddTraceExtra(logging.Filter):
    def __init__(self):
        super().__init__("trace")

    def filter(self, record: logging.LogRecord) -> bool:
        logger = current_logger.get()
        if not hasattr(record, self.name):
            trace_extra = TraceExtra(
                trace="info",
                elapsed=float(logger.value.elapsed) if logger else 0,
                details={},
                attachment=None
            )
            extra = vars(trace_extra)
            for k, v in extra.items():
                record.__dict__[k] = v

        return True
