# meta: These imports are required for the dynamic type resolution.
from .encode_log_entry import *
from .mutate_log_entry import *
from .. import TRACE_LEVEL


def configure(config: dict):
    """Configures logging and adds TRACE level not defined in the logging module by default."""
    import logging.config
    logging.addLevelName(TRACE_LEVEL, "TRACE")
    logging.config.dictConfig(config)
