from contextvars import ContextVar
from typing import Optional

from .types import (
    Logger,
    ContextExtra,
    TraceExtra,
    DefaultExtra,
    ExcInfo,
    Node,
    Metric,
)

current_logger: ContextVar[Optional[Node[Logger]]] = ContextVar("current_logger", default=None)
