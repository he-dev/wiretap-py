import logging
from typing import Optional, Callable

from . import filters
from . import json
from . import formatters

from .telemetry import begin_activity

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {activity_name} | {trace_name} | {activity_elapsed:.3f}s | {trace_message} | {trace_snapshot} | {trace_tags}"

DEFAULT_FILTERS: list[logging.Filter | Callable[[logging.LogRecord], bool]] = [
    filters.AddTimestampExtra(tz="utc"),
    filters.AddDefaultActivity(),
    filters.AddCurrentActivity(),
    filters.DumpException()
    # filters.FormatArgs(),
    # filters.FormatResult()
]


def dict_config(data: dict, default_filters: Optional[list[logging.Filter | Callable[[logging.LogRecord], bool]]] = None):
    import logging.config
    logging.config.dictConfig(data)
    for handler in logging.root.handlers:
        handler.filters = (default_filters or DEFAULT_FILTERS) + handler.filters
