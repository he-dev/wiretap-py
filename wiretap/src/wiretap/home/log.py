import logging

from wiretap.core import TRACE_LEVEL
from wiretap.core.span import Span


# node: Ignore duplicate code in these functions because they are too small to refactor.

# noinspection DuplicatedCode
def log_info(message: str, state: dict | None = None, **kwargs) -> None:
    Span.log_event(message=message, level=logging.INFO, state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_debug(message: str, state: dict | None = None, **kwargs) -> None:
    Span.log_event(message=message, level=logging.DEBUG, state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_trace(message: str, state: dict | None = None, **kwargs) -> None:
    Span.log_event(message=message, level=TRACE_LEVEL, state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_warning(message: str, state: dict | None = None, **kwargs) -> None:
    Span.log_event(message=message, level=logging.WARNING, state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_error(message: str, state: dict | None = None, **kwargs) -> None:
    Span.log_event(message=message, level=logging.ERROR, state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)
