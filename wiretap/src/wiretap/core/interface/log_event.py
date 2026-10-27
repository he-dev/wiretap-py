import logging
import sys

from wiretap.util.activity import ActivityScope


def log_event(
        message: str | None,
        level: int,
        state: dict | None,
        **kwargs
) -> None:
    logger = logging.getLogger(sys._getframe(2).f_code.co_name)

    if not logger.isEnabledFor(level):
        return

    scope = ActivityScope.get_current()

    context = scope.state.copy() if scope else {}
    if state:
        context.update(state)
    context.update(kwargs)

    extra = {
        "_wiretap": True,
        "context": context,
    }
    if scope:
        extra["trace"] = scope.trace

    logger.log(
        level=level,
        msg=message,
        exc_info=sys.exc_info()[0] is not None,
        extra=extra,
        stacklevel=3,
    )


# note: Ignore duplicate code for the below functions because they are too small to refactor.

# noinspection DuplicatedCode
def log_debug(message: str | None = None, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level=logging.DEBUG, state=state, **kwargs)


# noinspection DuplicatedCode
def log_info(message: str, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level=logging.INFO, state=state, **kwargs)


# noinspection DuplicatedCode
def log_warning(message: str, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level=logging.WARNING, state=state, **kwargs)


# noinspection DuplicatedCode
def log_error(message: str, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level=logging.ERROR, state=state, **kwargs)
