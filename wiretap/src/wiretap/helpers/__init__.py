import logging

from .. import current_block
from ..data import Block, Trace, BLOCK_KEY, TRACE_KEY


def get_block(record: logging.LogRecord) -> Block | None:
    # Try to get the feed from the record first otherwise the closest one.
    return record.__dict__.get(BLOCK_KEY, None) or getattr(current_block.get(), "value", None)


def get_trace(record: logging.LogRecord) -> Trace | None:
    # Try to get the feed from the record first otherwise the closest one.
    return record.__dict__.get(TRACE_KEY, None)
