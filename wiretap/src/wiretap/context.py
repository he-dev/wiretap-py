from contextvars import ContextVar

from _reusable import Node
from .contexts import ProcedureContext

current_procedure: ContextVar[Node[ProcedureContext] | None] = ContextVar("current_procedure", default=None)
