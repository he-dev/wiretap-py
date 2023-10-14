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
from .data import LoggerMeta, current_logger, LogRecordExtra

logging.root.addFilter(filter=filters.TimestampField())
logging.root.addFilter(filter=filters.LevelField())
logging.root.addFilter(filter=filters.ExtraFields())
logging.root.addFilter(filter=filters.SerializeDetailsField())


# class TestFormatter(logging.Formatter):
#    def format(self, record: logging.LogRecord) -> str:
#        return super().format(record)


def create_args_details(args: Optional[dict[str, Any]], args_format: Optional[dict[str, Optional[str]]]) -> dict[str, Any]:
    if not args:
        return {}

    if not args_format:
        return {}

    result = {key: format(args[key], args_format[key] or "") for key in args_format if not args[key] is None}
    return {"args": result} if result else {}


def create_result_details(result: Optional[Any], result_format: Optional[str]) -> dict[str, Any]:
    if result is None:
        return {}

    if result_format is None:
        return {}

    result = format(result_format or "")
    return {"result": result} if result else {}


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

        self._logger.addFilter(filter=filters.TimestampField())
        self._logger.addFilter(filter=filters.LevelField())
        self._logger.addFilter(filter=filters.ExtraFields())
        self._logger.addFilter(filter=filters.SerializeDetailsField())

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
            exc_info: Optional[ExcInfo] = None
    ):
        self._logger.setLevel(level)

        extra = LogRecordExtra(
            parent_id=self.parent.id if self.parent else None,
            unique_id=self.id,
            subject=self.subject,
            activity=self.activity,
            trace=name,
            elapsed=self.elapsed,
            details=(details or {}),
            attachment=attachment
        )

        self._logger.log(level=level, msg=message, exc_info=exc_info, extra=vars(extra))

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
            exc_info: Optional[ExcInfo] = None,
            group: Optional[str] = None
    ):
        pass


class _InitialTraceLogger:
    def __init__(self, log_trace: LogTrace):
        self._log_trace = log_trace

    def log_begin(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.INFO, group="initial")


class _ExtraTraceLogger:
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


class _FinalTraceLogger:
    def __init__(self, log_trace: LogTrace):
        self._log_trace = log_trace

    def log_noop(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.INFO, group="final")

    def log_abort(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.INFO, group="final")

    def log_end(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.INFO, group="final")

    def log_error(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
        self._log_trace(message, details, attachment, logging.ERROR, group="final", exc_info=_FinalTraceLogger._create_exc_info())

    @staticmethod
    def _create_exc_info() -> Optional[ExcInfo]:
        exc_cls, exc, exc_tb = sys.exc_info()
        if all((exc_cls, exc, exc_tb)):
            # the first 3 frames are the decorator traces; let's get rid of them
            while exc_tb.tb_next:
                exc_tb = exc_tb.tb_next
            return exc_cls, exc, exc_tb


class TraceLogger:
    def __init__(self, logger: Logger):
        self._logger = logger
        self._traces: set[str] = set()

    @property
    def initial(self) -> _InitialTraceLogger:
        return _InitialTraceLogger(self._log_trace)

    @property
    def active(self) -> _ExtraTraceLogger:
        return _ExtraTraceLogger(self._log_trace)

    @property
    def final(self) -> _FinalTraceLogger:
        return _FinalTraceLogger(self._log_trace)

    @property
    def default(self) -> Logger:
        return self._logger

    def _log_trace(
            self,
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None,
            level: int = logging.DEBUG,
            exc_info: Optional[ExcInfo] = None,
            group: Optional[str] = None
    ):
        if group in self._traces:
            return

        name = inspect.stack()[1][3]
        name = re.sub("^log_", "", name, flags=re.IGNORECASE)

        self._logger.log_trace(name, message, details, attachment, level, exc_info)
        self._traces.add(group)


@contextlib.contextmanager
def begin_telemetry(
        subject: Optional[str],
        activity: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        attachment: Optional[Any] = None
) -> ContextManager[TraceLogger]:
    """Begins a new activity context."""
    logger = Logger(subject, activity, current_logger.get())
    tracer = TraceLogger(logger)
    token = current_logger.set(logger)
    try:
        tracer.initial.log_begin(message, details, attachment)
        yield tracer
        tracer.final.log_end()
    except Exception as e:  # noqa
        tracer.final.log_error(message="Unhandled exception has occurred.")
        raise
    finally:
        current_logger.reset(token)


def telemetry(
        include_args: Optional[dict[str, Optional[str]]] = None,
        include_result: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        attachment: Optional[Any] = None
):
    """Provides telemetry for the decorated function."""

    def factory(decoratee):
        module = inspect.getmodule(decoratee)
        subject = module.__name__ if module else None
        activity = decoratee.__name__

        # print(decoratee.__name__)

        def inject_logger(logger: Logger, d: Dict):
            """Injects Logger if required."""
            for n, t in inspect.getfullargspec(decoratee).annotations.items():
                if t is Logger:
                    d[n] = logger
                if t is TraceLogger:
                    d[n] = TraceLogger(logger)

        def params(*decoratee_args, **decoratee_kwargs) -> Dict[str, Any]:
            # Zip arg names and their indexes up to the number of args of the decoratee_args.
            arg_pairs = zip(inspect.getfullargspec(decoratee).args, range(len(decoratee_args)))
            # Turn arg_pairs into a dictionary and combine it with decoratee_kwargs.
            return {t[0]: decoratee_args[t[1]] for t in arg_pairs} | decoratee_kwargs
            # No need to filter args as the logger is injected later.
            # return {k: v for k, v in result.items() if not isinstance(v, Logger)}

        if asyncio.iscoroutinefunction(decoratee):
            @functools.wraps(decoratee)
            async def decorator(*decoratee_args, **decoratee_kwargs):
                args_details = create_args_details(params(*decoratee_args, **decoratee_kwargs), include_args)
                with begin_telemetry(subject, activity, message=message, details=(details or {}) | args_details, attachment=attachment) as logger:
                    inject_logger(logger.default, decoratee_kwargs)
                    result = await decoratee(*decoratee_args, **decoratee_kwargs)
                    logger.final.log_end(details=create_result_details(result, include_result))
                    return result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

        else:
            @functools.wraps(decoratee)
            def decorator(*decoratee_args, **decoratee_kwargs):
                args_details = create_args_details(params(*decoratee_args, **decoratee_kwargs), include_args)
                with begin_telemetry(subject, activity, message=message, details=(details or {}) | args_details, attachment=attachment) as logger:
                    inject_logger(logger.default, decoratee_kwargs)
                    result = decoratee(*decoratee_args, **decoratee_kwargs)
                    logger.final.log_end(details=create_result_details(result, include_result))
                    return result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

    return factory
