import contextlib
import inspect
import logging
import sys
from typing import Any, Iterator, Type, Tuple

from .data import TraceTag
from .scopes.iteration_scope import IterationScope
from .scopes.telemetry_scope import TelemetryScope


def dict_config(config: dict):
    import logging.config
    logging.config.dictConfig(config)


@contextlib.contextmanager
def begin_scope(
        name: str | None = None,
        message: str | None = None,
        dump: dict[str, Any] | None = None,
        tags: set[Any] | None = None,
        **kwargs
) -> Iterator[TelemetryScope]:
    """
    This function logs telemetry for an activity scope.
    It returns the activity scope that provides additional APIs.
    """

    stack = inspect.stack(2)
    frame = stack[2]
    source = {
        "source": {
            "func": frame.function,
            "file": frame.filename,
            "line": frame.lineno
        }
    }

    custom_id = kwargs.pop("id", None)  # The caller can override the default id.

    dump = (dump or {}) | kwargs
    tags = (tags or set())

    # Keep it at debug level when there is nothing to log.
    start_level = logging.INFO if (dump or tags) else logging.DEBUG

    with TelemetryScope.push(custom_id, name, tags, frame) as scope:

        # Add some extra info when at debug level.
        tags = tags | ({TraceTag.AUTO} if scope.is_debug else set())

        try:

            scope.log_trace(
                event="start",
                message=message,
                dump=dump | (source if scope.is_debug else {}),
                tags=tags,
                level=start_level,
                is_final=False
            )

            yield scope
        except Exception:
            # exc_cls, exc, exc_tb = sys.exc_info()
            # if exc is not None:
            scope.log_exception(tags=tags, is_final=True)
            raise
        finally:
            # Add some extra info when at debug level.
            if scope.is_debug:
                dump |= {
                    "trace_count": {
                        "own": scope.trace_count_own + 1,  # The last one hasn't been counted yet.
                        "all": scope.trace_count_all + 1,
                    }
                }
            scope.log_trace(
                event="end",
                dump=dump,
                tags=tags,
                level=logging.INFO,
                is_final=True
            )


@contextlib.contextmanager
def begin_loop(
        name: str = "loop",
        message: str | None = None,
        tags: set[Any] | None = None,
        **kwargs
) -> Iterator[IterationScope]:
    """
    Initializes a new info-loop for telemetry and logs its details.
    """
    scope = IterationScope()
    try:
        yield scope
    finally:
        TelemetryScope.peek().log_basic(
            event=name,
            message=message,
            dump=scope.dump(),
            tags=(tags or set()) | {TraceTag.LOOP, TraceTag.AUTO},
            **kwargs
        )


@contextlib.contextmanager
def none_scope(
        name: str = "none",
        tags: set[Any] | None = None
) -> Iterator[TelemetryScope]:
    """
    Initializes a new none-scope for telemetry that doesn't log the two begin/clean traces.
    """
    stack = inspect.stack(2)
    frame = stack[2]
    with TelemetryScope.push(None, name, tags, frame) as scope:
        yield scope


def no_exc_info_if(exception_type: Type[BaseException] | Tuple[Type[BaseException], ...]) -> bool:
    exc_cls, exc, exc_tb = sys.exc_info()
    return not isinstance(exc, exception_type)


def to_tag(value: Any) -> str:
    return str(value).replace("_", "-")
