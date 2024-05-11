import logging
from typing import Optional, Callable

from . import specs
from . import filters
from . import process
from . import formatters
from . import tools
from .telemetry import begin_activity

DEFAULT_FORMAT = "{asctime}.{msecs:03.0f} {indent} {activity} | {event} | {elapsed:.3f}s | {message} | {snapshot}"

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
