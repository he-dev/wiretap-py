from collections import defaultdict
from contextvars import ContextVar
from typing import Tuple

from _reusable import Node
from .contexts import ProcedureContext

current_procedure: ContextVar[Node[ProcedureContext] | None] = ContextVar("current_procedure", default=None)
