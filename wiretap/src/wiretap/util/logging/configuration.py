# meta: These imports are required for the dynamic type resolution.
from .json_encoding import *
from .json_middleware import *


def configure(config: dict):
    """Configures logging and adds TRACE level not defined in the logging module by default."""
    import logging.config
    logging.config.dictConfig(config)
