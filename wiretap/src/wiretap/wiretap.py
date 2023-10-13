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
from datetime import datetime, date
from timeit import default_timer as timer
from types import TracebackType
from typing import Dict, Callable, Any, Protocol, Optional, Iterator, TypeVar, TypeAlias, Generic, ContextManager, Type

FormatOptions: TypeAlias = str | Callable[[Any], Any]
TValue = TypeVar("TValue")

DEFAULT_FORMATS: Dict[str, str] = {
    "classic": "{asctime}.{msecs:03.0f} | {levelname} | {module}.{funcName} | {message}",
    "wiretap": "{asctime}.{msecs:03.0f} {indent} {activity} | {trace} | {elapsed:.3f}s | {message} | {details} | node://{parent_id}/{unique_id} | {attachment}",
}

_scope: ContextVar[Optional["Logger"]] = ContextVar("_scope", default=None)


class SerializeDetails(Protocol):
    def __call__(self, value: Optional[Dict[str, Any]]) -> str | None: ...


class SerializeDetailsToJson(SerializeDetails):
    def __call__(self, value: Optional[Dict[str, Any]]) -> str | None:
        return json.dumps(value, sort_keys=True, allow_nan=False, cls=_JsonDateTimeEncoder) if value else None


class _JsonDateTimeEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, (date, datetime)):
            return o.isoformat()


class MultiFormatter(logging.Formatter):
    formats: Dict[str, str] = {}
    indent: str = "."
    values: Optional[Dict[str, Any]] = None
    serialize_details: SerializeDetails = SerializeDetailsToJson()

    def format(self, record: logging.LogRecord) -> str:
        record.levelname = record.levelname.lower()
        record.__dict__.update(self.values or {})  # Unpack values.

        if hasattr(record, "details") and isinstance(record.details, dict):
            record.indent = self.indent * record.__dict__.pop("_depth", 1)
            record.details = self.serialize_details(record.details)

        # determine which format to use
        format_key = "wiretap" if hasattr(record, "trace") else "classic"

        # use custom format if specified or the default one
        format_str = self.formats[format_key] if format_key in self.formats else DEFAULT_FORMATS[format_key]
        self._style._fmt = format_str

        return super().format(record)


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


class Logger:

    def __init__(self, module: Optional[str], activity: str, parent: Optional["Logger"] = None):
        self.id = uuid.uuid4()
        self.module = module
        self.activity = activity
        self.parent = parent
        self.depth = sum(1 for _ in self)
        self._start = timer()
        self._logger = logging.getLogger(f"{module}.{activity}")

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

        extra = {
            "parent_id": self.parent.id if self.parent else None,
            "unique_id": self.id,
            "subject": self.module,
            "activity": self.activity,
            "trace": name,
            "elapsed": self.elapsed,
            "details": (details or {}),
            "attachment": attachment,
            "_depth": self.depth
        }

        with _use_custom_log_record(_set_module_name(self.module), _set_func_name(self.activity)):
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
        module: Optional[str],
        name: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        attachment: Optional[Any] = None
) -> ContextManager[TraceLogger]:
    """Begins a new activity context."""
    logger = Logger(module, name, _scope.get())
    tracer = TraceLogger(logger)
    token = _scope.set(logger)
    try:
        tracer.initial.log_begin(message, details, attachment)
        yield tracer
        tracer.final.log_end()
    except Exception as e:  # noqa
        tracer.final.log_error(message="Unhandled exception has occurred.")
        raise
    finally:
        _scope.reset(token)


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
        module_name = module.__name__ if module else None
        scope_name = decoratee.__name__

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
                with begin_telemetry(module_name, scope_name, message=message, details=(details or {}) | args_details, attachment=attachment) as logger:
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
                with begin_telemetry(module_name, scope_name, message=message, details=(details or {}) | args_details, attachment=attachment) as logger:
                    inject_logger(logger.default, decoratee_kwargs)
                    result = decoratee(*decoratee_args, **decoratee_kwargs)
                    logger.final.log_end(details=create_result_details(result, include_result))
                    return result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

    return factory


@contextlib.contextmanager
def _use_custom_log_record(*actions: Callable[[logging.LogRecord], None]) -> ContextManager[None]:
    default = logging.getLogRecordFactory()

    def custom(*args, **kwargs):
        record = default(*args, **kwargs)
        for action in actions:
            action(record)
        return record

    logging.setLogRecordFactory(custom)
    try:
        yield
    finally:
        logging.setLogRecordFactory(default)


def _set_func_name(name: str):
    def set_value(record: logging.LogRecord):
        record.funcName = name

    return set_value


def _set_module_name(name: str):
    def set_value(record: logging.LogRecord):
        record.module = name

    return set_value
