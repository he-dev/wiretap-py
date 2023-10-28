from contextvars import ContextVar
from typing import Optional

from ..parts import Node
from ..tracing import Activity

current_activity: ContextVar[Optional[Node[Activity]]] = ContextVar("current_activity", default=None)


