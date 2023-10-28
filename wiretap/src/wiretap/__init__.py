import logging
from typing import Optional, Callable

from . import types
from . import filters
from . import session
from . import tracing
from .telemetry import telemetry, begin_telemetry, LogAbortWhen

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {activity} | {trace} | {elapsed:.3f}s | {message} | {details} | {attachment}"

DEFAULT_FILTERS: list[logging.Filter | Callable[[logging.LogRecord], bool]] = [
    filters.AddTimestampExtra(tz="utc"),
    filters.AddActivityExtra(),
    filters.AddNodeExtra(),
    filters.AddTraceExtra(),
    filters.FormatArgs(),
    filters.FormatResult()
]


def dict_config(data: dict, default_filters: Optional[list[logging.Filter | Callable[[logging.LogRecord], bool]]] = None):
    import logging.config
    logging.config.dictConfig(data)
    for handler in logging.root.handlers:
        handler.filters = (default_filters or DEFAULT_FILTERS) + handler.filters
