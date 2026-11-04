import logging
import sys

from wiretap.util.plot import PlotScope


def log_event(
        message: str | None,
        level: int,
        state: dict | None,
        **kwargs
) -> None:
    logger = logging.getLogger(sys._getframe(2).f_code.co_name)

    if not logger.isEnabledFor(level):
        return

    scope = PlotScope.get_current()

    context = scope.state.copy() if scope else {}
    context.update(state or {})
    context.update(kwargs)

    extra = {
        "_wiretap": True,
        "context": context or None,
        "trace": scope.trace.to_dict() if scope else None
    }

    logger.log(
        level=level,
        msg=message,
        exc_info=sys.exc_info()[0] is not None,
        extra=extra,
        stacklevel=3,
    )
