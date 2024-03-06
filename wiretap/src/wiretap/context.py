from contextvars import ContextVar

from wiretap.process import Activity, Node

current_activity: ContextVar[Node[Activity] | None] = ContextVar("current_activity", default=None)
