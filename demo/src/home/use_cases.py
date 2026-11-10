import time

from wiretap import Wiretap
from wiretap.data.content import BASELINE, INTERNAL

logger, wiretap = Wiretap.get(__name__)


def log_v13():
    logger.info("Message without activity.", extra=wiretap.snap("log_info", INTERNAL))
    with wiretap.begin_scope("outer", BASELINE, foo="bar") as outer:
        logger.debug(None, extra=outer.zero(INTERNAL))
        time.sleep(0.25)
        with wiretap.begin_scope("inner", BASELINE) as inner:
            logger.info(None, extra=inner.tick())
            logger.info("This zero comes after tick!", extra=inner.zero(INTERNAL))
            time.sleep(0.5)
            logger.info("Processed %s items in {activity[duration_ms]} ms.", 42, extra=inner.last())
            logger.info("This tick comes after last!", extra=inner.tick())
        time.sleep(0.25)
    logger.info("That's it.", extra=wiretap.snap("enough"))
