import asyncio
import contextlib
import dataclasses
import enum
import functools
import inspect
import json
import logging
import re
import sys
import uuid
from collections.abc import Generator
from contextvars import ContextVar
from datetime import datetime, date, timezone
from timeit import default_timer as timer
from types import TracebackType
from typing import Dict, Callable, Any, Protocol, Optional, Iterator, TypeVar, TypeAlias, Generic, ContextManager, Type
from . import filters
from .data import LoggerMeta, current_tracer, TraceExtra

logging.root.addFilter(filters.LowerLevelName())
logging.root.addFilter(filters.AddTimestampExtra())
logging.root.addFilter(filters.AddContextExtra())
logging.root.addFilter(filters.AddTraceExtra())

# class TestFormatter(logging.Formatter):
#    def format(self, record: logging.LogRecord) -> str:
#        return super().format(record)


ExcInfo: TypeAlias = tuple[Type[BaseException], BaseException, TracebackType]


class Logger(LoggerMeta):

    def __init__(self, subject: Optional[str], activity: str, parent: Optional[LoggerMeta] = None):
        self.id = uuid.uuid4()
        self.subject = subject
        self.activity = activity
        self.parent = parent
        self.depth = sum(1 for _ in self)
        self._start = timer()
        self._logger = logging.getLogger(f"{subject}.{activity}")

        self._logger.addFilter(filters.LowerLevelName())
        self._logger.addFilter(filters.AddTimestampExtra())
        self._logger.addFilter(filters.AddContextExtra())
        self._logger.addFilter(filters.AddTraceExtra())
        self._logger.addFilter(filters.FormatArgs())
        self._logger.addFilter(filters.FormatResult())
        self._logger.addFilter(filters.SkipDuplicateTrace())

    @property
    def elapsed(self) -> float:
        return timer() - self._start

    def log_trace(
            self,
            name: str,
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None,
            level: int = logging.DEBUG,
            exc_info: Optional[ExcInfo | bool] = None,
            extra: Optional[dict[str, Any]] = None
    ):
        self._logger.setLevel(level)

        trace_extra = TraceExtra(
            trace=name,
            elapsed=self.elapsed,
            details=(details or {}),
            attachment=attachment
        )

        extra = (extra or {}) | vars(trace_extra)

        self._logger.log(level=level, msg=message, exc_info=exc_info, extra=extra)

    def __iter__(self):
        current = self
        while current:
            yield current
            current = current.parent


class LogTrace(Protocol):
    def __call__(
            self,
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None,
            level: int = logging.DEBUG,
            exc_info: Optional[ExcInfo | bool] = None,
            group: Optional[str] = None,
            extra: Optional[dict[str, Any]] = None
    ):
        pass


class InitialTraceLogger:
    def __init__(self, log_trace: LogTrace):
        self._log_trace = log_trace

    def log_begin(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None, inputs: Optional[dict[str, Any]] = None, inputs_spec: Optional[dict[str, str | Callable | None]] = None) -> None:
        self._log_trace(message, details, attachment, logging.INFO, group="initial", extra=dict(inputs=inputs, inputs_spec=inputs_spec))


class OtherTraceLogger:
    def __init__(self, log_trace: LogTrace):
        self._log_trace = log_trace

    def log_info(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.DEBUG)

    def log_item(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.DEBUG)

    def log_skip(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.DEBUG)

    def log_metric(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.DEBUG)


class FinalTraceLogger:
    def __init__(self, log_trace: LogTrace):
        self._log_trace = log_trace

    def log_noop(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.INFO, group="final")

    def log_abort(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.INFO, group="final")

    def log_end(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None, output: Optional[Any] = None, output_spec: Optional[str | Callable | None] = None) -> None:
        self._log_trace(message, details, attachment, logging.INFO, group="final", extra=dict(output=output, output_spec=output_spec))

    def log_error(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.ERROR, group="final", exc_info=True)


class TraceLogger:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.traces: set[str] = set()

    @property
    def initial(self) -> InitialTraceLogger:
        return InitialTraceLogger(self._log_trace)

    @property
    def other(self) -> OtherTraceLogger:
        return OtherTraceLogger(self._log_trace)

    @property
    def final(self) -> FinalTraceLogger:
        return FinalTraceLogger(self._log_trace)

    @property
    def default(self) -> Logger:
        return self.logger

    def _log_trace(
            self,
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None,
            level: int = logging.DEBUG,
            exc_info: Optional[ExcInfo | bool] = None,
            group: Optional[str] = None,
            extra: Optional[dict[str, Any]] = None
    ):
        name = inspect.stack()[1][3]
        name = re.sub("^log_", "", name, flags=re.IGNORECASE)

        self.logger.log_trace(name, message, details, attachment, level, exc_info, extra)
        self.traces.add(group)


@contextlib.contextmanager
def telemetry_context(
        subject: str,
        activity: str
) -> ContextManager[TraceLogger]:
    parent = current_tracer.get()
    logger = Logger(subject, activity, parent.logger if parent else None)
    tracer = TraceLogger(logger)
    token = current_tracer.set(tracer)
    try:
        yield tracer
    except Exception as e:  # noqa
        tracer.final.log_error(message="Unhandled exception has occurred.")
        raise
    finally:
        current_tracer.reset(token)


@contextlib.contextmanager
def begin_telemetry(
        subject: str,
        activity: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        attachment: Optional[Any] = None
) -> ContextManager[TraceLogger]:
    with telemetry_context(subject, activity) as tracer:
        tracer.initial.log_begin(message, details, attachment)
        yield tracer
        tracer.final.log_end()


def telemetry(
        include_args: Optional[dict[str, Optional[str]]] = None,
        include_result: Optional[str | bool] = None,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        attachment: Optional[Any] = None
):
    """Provides telemetry for the decorated function."""

    if isinstance(include_result, bool) and include_result:
        include_result = ""

    def factory(decoratee):
        module = inspect.getmodule(decoratee)
        subject = module.__name__ if module else None
        activity = decoratee.__name__

        # print(decoratee.__name__)

        def inject_logger(logger: TraceLogger, d: Dict):
            """Injects Logger if required."""
            for n, t in inspect.getfullargspec(decoratee).annotations.items():
                if t is Logger:
                    d[n] = logger.default
                if t is TraceLogger:
                    d[n] = logger

        def get_args(*decoratee_args, **decoratee_kwargs) -> dict[str, Any]:
            # Zip arg names and their indexes up to the number of args of the decoratee_args.
            arg_pairs = zip(inspect.getfullargspec(decoratee).args, range(len(decoratee_args)))
            # Turn arg_pairs into a dictionary and combine it with decoratee_kwargs.
            return {t[0]: decoratee_args[t[1]] for t in arg_pairs} | decoratee_kwargs
            # No need to filter args as the logger is injected later.
            # return {k: v for k, v in result.items() if not isinstance(v, Logger)}

        if asyncio.iscoroutinefunction(decoratee):
            @functools.wraps(decoratee)
            async def decorator(*decoratee_args, **decoratee_kwargs):
                args = get_args(*decoratee_args, **decoratee_kwargs)
                with telemetry_context(subject, activity) as logger:
                    logger.initial.log_begin(message=message, details=details or {}, attachment=attachment, inputs=args, inputs_spec=include_args)
                    inject_logger(logger, decoratee_kwargs)
                    result = await decoratee(*decoratee_args, **decoratee_kwargs)
                    logger.final.log_end(output=result, output_spec=include_result)
                    return result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

        else:
            @functools.wraps(decoratee)
            def decorator(*decoratee_args, **decoratee_kwargs):
                args = get_args(*decoratee_args, **decoratee_kwargs)
                with telemetry_context(subject, activity) as logger:
                    logger.initial.log_begin(message=message, details=details or {}, attachment=attachment, inputs=args, inputs_spec=include_args)
                    inject_logger(logger, decoratee_kwargs)
                    result = decoratee(*decoratee_args, **decoratee_kwargs)
                    logger.final.log_end(output=result, output_spec=include_result)
                    return result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

    return factory
