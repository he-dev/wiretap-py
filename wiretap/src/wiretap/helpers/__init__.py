import logging
from typing import Tuple

from _reusable import Node
from .. import current_procedure
from ..data import Procedure, WIRETAP_KEY, Trace, Entry


def unpack(record: logging.LogRecord) -> Tuple[Procedure | None, Trace | None]:
    # Try to get an entry from the record.
    entry: Entry | None = record.__dict__.get(WIRETAP_KEY, None)
    if entry:
        return entry.procedure, entry.trace

    # Try to get the nearest procedure.
    node: Node | None = current_procedure.get()
    if node:
        return node.value, None

    # There is no procedure in scope.
    return None, None
