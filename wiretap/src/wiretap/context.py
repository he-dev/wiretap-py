from contextvars import ContextVar

from wiretap.tools import Node
from wiretap.tracing import Activity

current_activity: ContextVar[Node["Activity"] | None] = ContextVar("current_activity", default=None)
