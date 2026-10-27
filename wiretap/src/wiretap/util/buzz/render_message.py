import logging

from wiretap.meta import FormatData


def render_message(record: logging.LogRecord) -> str | None:
    if not record.__dict__.get("_wiretap", False):
        return record.getMessage()

    if record.msg is None:
        return None

    return str(record.msg).format_map(FormatData(record.__dict__))
