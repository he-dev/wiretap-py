import logging
from enum import Enum, auto

TRACE_LEVEL = 5


class SpanStatus(str, Enum):
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"

    def __str__(self):
        return self.value


def configure(config: dict):
    """Configures logging and adds TRACE level not defined in the logging module by default."""
    import logging.config
    logging.addLevelName(TRACE_LEVEL, "TRACE")
    logging.config.dictConfig(config)


class NoActivityInScopeError(Exception):
    pass
