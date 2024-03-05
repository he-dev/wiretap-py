import logging


class AddTraceExtra(logging.Filter):
    def __init__(self):
        super().__init__("trace")

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "trace"):
            extra = dict(
                trace="plain",
                elapsed=0,
                snapshot={},
            )
            for k, v in extra.items():
                record.__dict__[k] = v

        return True
