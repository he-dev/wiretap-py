import time

from wiretap import Wiretap
from wiretap.core.channel import INTERNAL, OFFICIAL

logger, wiretap = Wiretap.get(__name__)


def log_v13():
    logger.info("Message without activity.", extra=wiretap.snap("log_info", INTERNAL))
    with wiretap.begin_scope(about="outer", channel=OFFICIAL, foo="bar") as outer:
        logger.debug(None, extra=outer.zero())
        time.sleep(0.25)
        with wiretap.begin_scope("inner", OFFICIAL) as inner:
            logger.info(None, extra=inner.tick())
            logger.info("This zero comes after tick!", extra=inner.zero())
            time.sleep(0.5)
            logger.info("Processed %s items in {activity[duration_ms]} ms.", 42, extra=inner.last())
            logger.info("This tick comes after last!", extra=inner.tick())
        time.sleep(0.25)
    logger.info("That's it.", extra=wiretap.snap("enough", INTERNAL))
