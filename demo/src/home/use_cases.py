from wiretap import Wiretap

logger, wiretap = Wiretap.get(__name__)


def log_v13():
    logger.info("Message without activity.", extra=wiretap.snap("log_info", "internal"))
    with wiretap.begin_scope(about="outer", buzzing="regular", foo="bar") as outer:
        logger.debug(None, extra=outer.zero())
        with wiretap.begin_scope("inner", "regular") as inner:
            logger.info(None, extra=inner.tick())
            logger.info("This zero comes after tick!", extra=inner.zero())
            logger.info("Processed %s items in {activity[duration_ms]} ms.", 42, extra=inner.last())
            logger.info("This tick comes after last!", extra=inner.tick())
    logger.info("That's it.", extra=wiretap.snap("enough", "internal"))
