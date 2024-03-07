import logging
import traceback


class DumpException(logging.Filter):
    def __init__(self):
        super().__init__("dump_exception")

    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info:
            exc_cls, exc, exc_tb = record.exc_info
            # format_exception return a list of lines. Join it a single sing or otherwise an array will be logged.
            record.__dict__["exception"] = "".join(traceback.format_exception(exc_cls, exc, exc_tb))

        return True
