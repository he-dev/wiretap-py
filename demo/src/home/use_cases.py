from wiretap import Storyline

logger, storyline = Storyline.logger(__name__)


def log_v13():
    logger.info("Message without plot.", extra=storyline.snap("log_info", "buzz"))
    with storyline.begin_plot(about="outer", story="core", foo="bar") as outer:
        logger.debug(None, extra=outer.zero())
        with storyline.begin_plot("inner", "core") as inner:
            logger.info(None, extra=inner.tick())
            logger.info("Processed %s items in {plot[duration_ms]} ms.", 42, extra=inner.last())
    logger.info("That's it.", extra=storyline.snap("enough", "buzz"))
