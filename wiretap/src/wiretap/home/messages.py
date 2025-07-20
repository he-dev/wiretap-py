import logging
from typing import Optional

from wiretap.core import TRACE_LEVEL
from wiretap.core.activity_scope import ActivityScope


def log_info(message: str, state: Optional[dict] = None, **kwargs) -> None:
    ActivityScope.log_event(message=message, level=logging.INFO, state=state, frame_at=2, **kwargs)


def log_debug(message: str, state: Optional[dict] = None, **kwargs) -> None:
    ActivityScope.log_event(message=message, level=logging.DEBUG, state=state, frame_at=2, **kwargs)


def log_trace(message: str, state: Optional[dict] = None, **kwargs) -> None:
    ActivityScope.log_event(message=message, level=TRACE_LEVEL, state=state, frame_at=2, **kwargs)


def log_warning(message: str, state: Optional[dict] = None, **kwargs) -> None:
    ActivityScope.log_event(message=message, level=logging.WARNING, state=state, frame_at=2, **kwargs)


def log_error(message: str, state: Optional[dict] = None, **kwargs) -> None:
    ActivityScope.log_event(message=message, level=logging.ERROR, state=state, frame_at=2, **kwargs)
