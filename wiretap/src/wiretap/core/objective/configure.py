def configure(config: dict):
    """Configures standard Python logging."""
    import logging.config
    logging.config.dictConfig(config)
