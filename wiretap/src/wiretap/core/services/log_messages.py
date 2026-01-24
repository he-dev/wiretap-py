import inspect
import logging
import sys

from wiretap.util.span import Span, LogLevelName, TRACE_LEVEL, SpanEvent, NoSpanInScopeError


# note: Ignore duplicate code in these functions because they are too small to refactor.


def log_event(
        message: str | None = None,
        level: LogLevelName = "info",
        state: dict | None = None,
        frame_at: int | None = None,
        **kwargs
) -> None:
    _level = _map_level_name_to_int(level)

    if span := Span.current():
        # meta: Not using due to bad performance.
        # stack = inspect.stack(2)
        # frame = stack[frame_at] if frame_at else scope.frame

        # core: Fetch the current frame in case logging is called by a method without its own span.
        # meta: Avoids inspect.stack for performance reasons.
        frame = sys._getframe(frame_at or 1)
        info = inspect.getframeinfo(frame)
        frame = inspect.FrameInfo(frame, info.filename, info.lineno, info.function, info.code_context, info.index)

        span.logger.log(
            level=_level,
            msg=message,
            exc_info=_level >= logging.ERROR or sys.exc_info()[0] is not None,
            extra={
                SpanEvent.KEY: SpanEvent(span=span, frame=frame, state=state, **kwargs)
            }
        )
    else:
        raise NoSpanInScopeError("Cannot log event because there is no activity in scope.")


# noinspection DuplicatedCode
def log_info(message: str, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level="info", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_debug(message: str, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level="debug", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_trace(message: str, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level="trace", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_warning(message: str, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level="warning", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_error(message: str, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level="error", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_critical(message: str, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level="critical", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


def _map_level_name_to_int(level: LogLevelName) -> int:
    match level:
        case "off":
            return logging.NOTSET
        case "trace":
            return TRACE_LEVEL
        case "debug":
            return logging.DEBUG
        case "info":
            return logging.INFO
        case "warning":
            return logging.WARNING
        case "error":
            return logging.ERROR
        case "critical":
            return logging.CRITICAL
        case _:
            raise ValueError(f"Invalid log level: {level}")
