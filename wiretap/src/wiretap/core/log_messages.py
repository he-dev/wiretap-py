import inspect
import logging
import sys
from types import FrameType

from wiretap.meta import trim_path
from wiretap.util.activity import ActivityScope, ActivityEvent


def log_event(
        message: str | None,
        level: int,
        state: dict | None,
        frame_at: int | None,
        **kwargs
) -> None:
    # meta: Not using these due to bad performance.
    # stack = inspect.stack(2)
    # frame = stack[frame_at] if frame_at else scope.frame

    # core: Fetch the current frame in case logging is called by a method without its own span.
    # meta: Avoids inspect.stack for performance reasons.
    frame_type: FrameType = sys._getframe(frame_at or 1)
    info = inspect.getframeinfo(frame_type)
    frame: inspect.FrameInfo = inspect.FrameInfo(
        frame_type,
        info.filename,
        info.lineno,
        info.function,
        info.code_context,
        info.index
    )

    extra = kwargs | (state or {}) | {
        "source": {
            "func": frame.function,
            "file": trim_path(frame.filename),
            "line": frame.lineno
        }
    }

    logging.getLogger(frame.function).log(
        level=level,
        msg=message,
        exc_info=level >= logging.ERROR or sys.exc_info()[0] is not None,
        extra={"_wiretap": extra}
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
