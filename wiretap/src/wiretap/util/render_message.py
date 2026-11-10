import logging

from wiretap.data.missing import FormatData


def render_message(record: logging.LogRecord) -> str | None:
    message = record.getMessage()
    if not record.__dict__.get("_format_map", False):
        return message

    if record.msg is None:
        return None

    return message.format_map(FormatData(record.__dict__))
