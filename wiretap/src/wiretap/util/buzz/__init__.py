# meta: These imports are required for the dynamic type resolution.
from .encode_json import *
from .build_json import *


def configure(config: dict):
    """Configures logging and adds TRACE level not defined in the logging module by default."""
    import logging.config
    logging.config.dictConfig(config)
