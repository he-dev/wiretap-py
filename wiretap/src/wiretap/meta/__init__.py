import logging
from typing import Literal

TRACE_LEVEL = 5

LogLevelName = Literal["off", "trace", "debug", "info", "warning", "error", "critical"]


def map_level_name_to_int(level: LogLevelName) -> int:
    match level:
        case "off":
            return logging.NOTSET
        case "trace":
            return TRACE_LEVEL
        case "debug":
            return logging.DEBUG
        case "info":
            return logging.INFO
        case "warning":
            return logging.WARNING
        case "error":
            return logging.ERROR
        case "critical":
            return logging.CRITICAL
        case _:
            raise ValueError(f"Invalid duration level: {level}")
