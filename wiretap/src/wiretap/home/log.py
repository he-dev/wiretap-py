from typing import Callable

from wiretap.core.span import Span
from wiretap.home.begin import DurationLevel


# node: Ignore duplicate code in these functions because they are too small to refactor.

# noinspection DuplicatedCode
def log_info(message: str, state: dict | None = None, **kwargs) -> None:
    Span.log_event(message=message, level="info", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_debug(message: str, state: dict | None = None, **kwargs) -> None:
    Span.log_event(message=message, level="debug", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_trace(message: str, state: dict | None = None, **kwargs) -> None:
    Span.log_event(message=message, level="trace", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_warning(message: str, state: dict | None = None, **kwargs) -> None:
    Span.log_event(message=message, level="warning", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_error(message: str, state: dict | None = None, **kwargs) -> None:
    Span.log_event(message=message, level="error", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_critical(message: str, state: dict | None = None, **kwargs) -> None:
    Span.log_event(message=message, level="critical", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


def log_duration(level: DurationLevel = "info") -> Callable[[Span], None]:
    """
    Logs the duration of a span at the specified log level when the span ends.

    Args:
        level: The log level at which the duration event will be recorded. Must be a valid log level recognized by the system.

    Returns:
        A function that, when invoked with a Span object, logs the duration and other details of the span.

    Raises:
        ValueError: If the provided log level is invalid.
    """

    # core: Check duration level early to throw a potential exception right away and not at the end.
    _ensure_duration_level_in_range(level)

    def _log_duration(span: Span) -> None:
        Span.log_event(
            message=f"Status: {span.status}, Duration: {span.stopwatch.duration_ms} ms.",
            frame_at=0,
            level=level,
            event="end_span"
        )

    return _log_duration


def _ensure_duration_level_in_range(level: DurationLevel | None) -> None:
    match level:
        case None:
            pass  # core: OK
        case "info":
            pass  # core: OK
        case "debug":
            pass  # core: OK
        case "trace":
            pass  # core: OK
        case _:
            raise ValueError(f"Invalid duration level: {level}")
