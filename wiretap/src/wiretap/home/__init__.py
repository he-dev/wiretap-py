from wiretap.core import TRACE_LEVEL


def configure(config: dict):
    import logging.config
    logging.addLevelName(TRACE_LEVEL, "TRACE")
    logging.config.dictConfig(config)
