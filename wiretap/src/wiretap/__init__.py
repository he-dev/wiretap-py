import contextlib
import inspect
import sys
from typing import Any, Iterator, Type, Tuple, ContextManager, Callable

from .context import current_block
from .contexts import BlockContext
from .contexts.iteration import IterationContext
from .data import TraceLevel, TraceTag, LogTrace, Block
from _reusable import Node


def dict_config(config: dict):
    import logging.config
    logging.config.dictConfig(config)


@contextlib.contextmanager
def log_begin(
        name: str | None = None,
        message: str | None = None,
        tags: set[Any] | None = None
) -> Iterator[BlockContext]:
    """This function logs telemetry for an activity scope. It returns the activity scope that provides additional APIs."""
    stack = inspect.stack(2)
    frame = stack[2]
    parent = current_block.get()

    scope = BlockContext(
        frame=frame,
        parent=parent.value if parent else None,
        name=name or frame.function,
        tags=tags,
    )
    token = current_block.set(Node(value=scope, parent=parent, id=scope.id))
    try:
        scope.log_info(
            name="begin",
            message=message,
            state={
                "func": frame.function,
                "file": frame.filename,
                "line": frame.lineno
            },
            tags=tags or {}
        )
        yield scope
    except Exception:
        exc_cls, exc, exc_tb = sys.exc_info()
        if exc is not None:
            scope.log_exception()
        raise
    finally:
        scope.log_info(name="end", in_progress=False)
        current_block.reset(token)


@contextlib.contextmanager
def _log_begin(
        message: str | None,
        block: BlockContext,
        log_trace: LogTrace
) -> Iterator[BlockContext]:
    """This function logs telemetry for an activity scope. It returns the activity scope that provides additional APIs."""

    token = current_block.set(Node(value=block, parent=block.parent, id=block.id))
    try:
        log_trace(
            name="begin",
            message=message,
            state={
                "func": block.frame.function,
                "file": block.frame.filename,
                "line": block.frame.lineno
            },
            tags=set()
        )
        yield block
    except Exception:
        exc_cls, exc, exc_tb = sys.exc_info()
        if exc is not None:
            block.log_exception()
        raise
    finally:
        log_trace(name="end", in_progress=False)
        current_block.reset(token)


def info_block(
        name: str | None = None,
        message: str | None = None,
        tags: set[Any] | None = None
) -> ContextManager[BlockContext]:
    stack = inspect.stack(2)
    frame = stack[1]
    parent = current_block.get()

    block = BlockContext(
        frame=frame,
        parent=parent.value if parent else None,
        name=name or frame.function,
        tags=tags,
    )

    return _log_begin(message, block, block.log_info)


def debug_block(
        name: str | None = None,
        message: str | None = None,
        tags: set[Any] | None = None
) -> ContextManager[BlockContext]:
    pass


@contextlib.contextmanager
def info_loop(
        counter_name: str | None = None,
        message: str | None = None,
        tags: set[Any] | None = None,
        **kwargs
) -> Iterator[IterationContext]:
    loop = IterationContext(counter_name)
    try:
        yield loop
    finally:
        block: BlockContext = current_block.get().value
        block.log_info(
            name="loop",
            message=message,
            state=loop.dump(),
            tags=(tags or set()) | {TraceTag.LOOP},
            **kwargs
        )


def closest() -> BlockContext:
    # todo: wrap it in a new scope but don't log any traces
    return current_block.get().value


@contextlib.contextmanager
def none_block(
        name: str | None = None,
        tags: set[Any] | None = None
) -> Iterator[BlockContext]:
    stack = inspect.stack(2)
    frame = stack[2]
    parent = current_block.get()

    block = BlockContext(
        frame=frame,
        parent=parent.value if parent else None,
        name=name or frame.function,
        tags=tags,
    )

    token = current_block.set(Node(value=block, parent=block.parent, id=block.id))
    try:
        yield block
    finally:
        current_block.reset(token)


def no_exc_info_if(exception_type: Type[BaseException] | Tuple[Type[BaseException], ...]) -> bool:
    exc_cls, exc, exc_tb = sys.exc_info()
    return not isinstance(exc, exception_type)


def to_tag(value: Any) -> str:
    return str(value).replace("_", "-")
