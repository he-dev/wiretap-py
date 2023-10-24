import logging
from typing import Optional

from . import types
from . import filters
from . import session
from .loggers import BasicLogger, TraceLogger
from .telemetry import telemetry, begin_telemetry, LogAbortWhen

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {activity} | {trace} | {elapsed:.3f}s | {message} | {details} | node://{parent_id}/{unique_id} | {attachment}"

DEFAULT_FILTERS = [
    filters.AddTimestampExtra(tz="utc"),
    filters.AddContextExtra(),
    filters.AddTraceExtra(),
    filters.FormatArgs(),
    filters.FormatResult()
]


def dict_config(data: dict, default_filters: Optional[list[logging.Filter]] = None):
    import logging.config
    logging.config.dictConfig(data)
    for handler in logging.root.handlers:
        handler.filters = (default_filters or DEFAULT_FILTERS) + handler.filters
