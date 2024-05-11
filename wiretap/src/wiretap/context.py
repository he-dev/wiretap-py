from contextvars import ContextVar

from wiretap.process import ActivityScope, Node

current_activity: ContextVar[Node[ActivityScope] | None] = ContextVar("current_activity", default=None)
