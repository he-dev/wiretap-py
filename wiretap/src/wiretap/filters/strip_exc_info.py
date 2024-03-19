import logging


class StripExcInfo(logging.Filter):
    def __init__(self):
        super().__init__("exc_info")

    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info:
            exc_cls, exc, exc_tb = record.exc_info

            # drop the decorator frame
            if all((exc_cls, exc, exc_tb)):
                if "telemetry.py" in exc_tb.tb_frame.__str__():
                    exc_tb = exc_tb.tb_next

            record.exc_info = exc_cls, exc, exc_tb  # type: ignore
        return True
