from contextvars import ContextVar

from _reusable import Node
from .scopes import ActivityScope

current_activity: ContextVar[Node[ActivityScope] | None] = ContextVar("current_activity", default=None)

