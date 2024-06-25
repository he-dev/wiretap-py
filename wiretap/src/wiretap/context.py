from contextvars import ContextVar

from _reusable import Node
from .contexts import ActivityContext

current_activity: ContextVar[Node[ActivityContext] | None] = ContextVar("current_activity", default=None)

