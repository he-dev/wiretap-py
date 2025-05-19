import contextlib
import inspect
import logging
from typing import Any, Iterator, Callable

from .data import TraceTag, LoopStats
from .scopes.telemetry_scope import TelemetryScope
from .scopes.iteration_scope import LoopScope
from .stats.basic import BasicStats
from .stats.welford import WelfordStats


def dict_config(config: dict):
    import logging.config
    logging.config.dictConfig(config)


@contextlib.contextmanager
def begin_scope(
        name: str | None = None,
        message: str | None = None,
        dump: dict[str, Any] | None = None,
        tags: set[Any] | None = None,
        debug: bool = False,
        **kwargs
) -> Iterator[TelemetryScope]:
    """
    Initializes a new telemetry scope and logs its start, exception, and end.
    This can be disabled by setting the 'lite' parameter to True.

    :param name: The name of the scope. If None, the name will be derived from the calling frame. Usually the function name.
    :param message: The message to log when the scope starts.
    :param dump: A dictionary of extra data to log that is attached to each trace.
    :param tags: A set of tags to associate with the loop that is attached to each trace.
    :param kwargs: Additional keyword arguments to be passed to each trace.
    :param debug: If True, the scope will log its start, exception, or end traces at the debug level.

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
    scope_level = logging.DEBUG if debug else logging.INFO

    with TelemetryScope.push(custom_id, name, dump, tags, frame) as scope:

        # Add some extra info when at debug level.
        tags = tags | ({TraceTag.AUTO} if scope.is_debug else set())

        try:
            scope.log_trace(
                name="start",
                message=message,
                dump=(source if scope.is_debug else {}),
                tags=tags,
                level=scope_level,
                is_final=False
            )

            yield scope
        except Exception:
            # exc_cls, exc, exc_tb = sys.exc_info()
            # if exc is not None:
            scope.log_error(tags=tags, is_final=True)
            raise
        finally:
            # Add some extra info when at debug level.
            # if scope.is_debug:
            #     dump |= {
            #         "trace_count": {
            #             "own": scope.trace_count_own + 1, # The last one hasn't been counted yet.
            #             "all": scope.trace_count_all + 1,
            #         }
            #     }

            scope.log_trace(
                name="end",
                # dump=dump,
                tags=tags,
                level=scope_level,
                is_final=True
            )


@contextlib.contextmanager
def begin_loop(
        name: str,
        message: str | None = None,
        dump: dict[str, Any] | None = None,
        tags: set[Any] | None = None,
        stats: Callable[[], LoopStats] = lambda: WelfordStats(),
        **kwargs
) -> Iterator[LoopScope]:
    """
    Initializes a new info-loop for telemetry and logs its details.

    :param name: The name of the loop.
    :param message: The message to log when the loop starts.
    :param dump: A dictionary of extra data to log that is attached to each trace.
    :param tags: A set of tags to associate with the loop that is attached to each trace.
    :param stats: Factory function that creates a new stats object.
    :param kwargs: Additional keyword arguments to be passed to each trace.
    """

    stack = inspect.stack(2)
    frame = stack[2]

    dump = (dump or {}) | kwargs
    tags = (tags or set()) | {TraceTag.LOOP}

    custom_id = kwargs.pop("id", None)

    if not TelemetryScope.peek():
        raise Exception("Cannot create a loop scope outside of a telemetry scope.")

    with TelemetryScope.push(custom_id, name, dump, tags, frame) as scope:
        loop = LoopScope(name=name, dump=dump, tags=tags, stats=stats())
        try:
            scope.log_trace(
                name="start",
                message=message,
                level=logging.INFO if message else logging.DEBUG,
            )
            yield loop
        finally:
            scope.log_trace(
                name="end",
                dump=loop.dump()
            )
