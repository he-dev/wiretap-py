from contextvars import ContextVar
from typing import Optional

from ..parts import Node
from ..types import Logger

current_logger: ContextVar[Optional[Node[Logger]]] = ContextVar("current_logger", default=None)


