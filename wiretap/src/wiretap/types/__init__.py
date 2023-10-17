from contextvars import ContextVar
from typing import Optional

from .types import (
    Logger,
    Tracer,
    ContextExtra,
    TraceExtra,
    InitialExtra,
    DefaultExtra,
    FinalExtra,
    ExcInfo
)

current_tracer: ContextVar[Optional[Tracer]] = ContextVar("current_tracer", default=None)
