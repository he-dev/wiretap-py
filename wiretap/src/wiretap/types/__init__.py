from contextvars import ContextVar
from typing import Optional

from .types import (
    Logger,
    ContextExtra,
    TraceExtra,
    InitialExtra,
    DefaultExtra,
    FinalExtra,
    ExcInfo,
    Node,
    Metric,
)

current_logger: ContextVar[Optional[Logger]] = ContextVar("current_logger", default=None)
