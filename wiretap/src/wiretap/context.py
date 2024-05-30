from contextvars import ContextVar
from typing import Type

from .scopes import ActivityScope
from _reusable import Node

current_activity: ContextVar[Node[ActivityScope] | None] = ContextVar("current_activity", default=None)

