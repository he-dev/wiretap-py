import contextlib
import inspect
import logging
from typing import Any, Iterator

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
        lite: bool = False,
        **kwargs
) -> Iterator[TelemetryScope]:
    """
    Initializes a new telemetry scope and logs its start, exception, and end.
    This can be disabled by setting the 'lite' parameter to True.
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

            if not lite:
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
            if not lite:
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

            if not lite:
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
    if telemetry := TelemetryScope.peek():
        iteration = IterationScope()
        try:
            yield iteration
        finally:
            telemetry.log_basic(
                event=name,
                message=message,
                dump=iteration.dump(),
                tags=(tags or set()) | ({TraceTag.LOOP, TraceTag.AUTO} if telemetry.is_debug else set()),
                **kwargs
            )
    else:
        raise Exception("Cannot create a loop scope outside of a telemetry scope.")
