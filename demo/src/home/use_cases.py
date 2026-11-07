from wiretap import Wiretap

logger, wiretap = Wiretap.get(__name__)


def log_v13():
    logger.info("Message without activity.", extra=wiretap.snap("log_info", "buzz"))
    with wiretap.begin_scope(about="outer", focus="core", foo="bar") as outer:
        logger.debug(None, extra=outer.zero())
        with wiretap.begin_scope("inner", "core") as inner:
            logger.info(None, extra=inner.tick())
            logger.info("This zero comes after tick!", extra=inner.zero())
            logger.info("Processed %s items in {activity[duration_ms]} ms.", 42, extra=inner.last())
            logger.info("This tick comes after last!", extra=inner.tick())
    logger.info("That's it.", extra=wiretap.snap("enough", "buzz"))
