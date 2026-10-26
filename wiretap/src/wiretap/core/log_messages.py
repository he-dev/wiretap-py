import logging
import sys


def log_event(
        message: str | None,
        level: int,
        state: dict | None,
        frame_at: int | None,
        **kwargs
) -> None:
    func_name = sys._getframe(2).f_code.co_name
    extra = kwargs | (state or {})
    logging.getLogger(func_name).log(
        level=level,
        msg=message,
        exc_info=level >= logging.ERROR or sys.exc_info()[0] is not None,
        extra=extra,
        stacklevel=1
    )


# note: Ignore duplicate code for the below functions because they are too small to refactor.

# noinspection DuplicatedCode
def log_debug(message: str | None = None, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level=logging.DEBUG, state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_info(message: str, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level=logging.INFO, state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_warning(message: str, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level=logging.WARNING, state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_error(message: str, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level=logging.ERROR, state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)
