from enum import Enum

from wiretap.modules.span import TRACE_LEVEL


def configure(config: dict):
    """Configures logging and adds TRACE level not defined in the logging module by default."""
    import logging.config
    logging.addLevelName(TRACE_LEVEL, "TRACE")
    logging.config.dictConfig(config)
