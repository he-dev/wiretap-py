from contextvars import ContextVar

from _reusable import Node
from .contexts import BlockContext

current_block: ContextVar[Node[BlockContext] | None] = ContextVar("current_block", default=None)
