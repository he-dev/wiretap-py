from contextvars import ContextVar

from .activity import Activity
from _reusable import Node

current_activity: ContextVar[Node[Activity] | None] = ContextVar("current_activity", default=None)
