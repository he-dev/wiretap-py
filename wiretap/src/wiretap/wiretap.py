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
from typing import Dict, Callable, Any, Protocol, Optional, Iterator, TypeVar, TypeAlias, Generic, ContextManager

FormatOptions: TypeAlias = str | Callable[[Any], Any] | None
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


def multi_format(value: Any, value_format: FormatOptions) -> Optional[Any]:
    if value is None:
        # cancel as there is no value to format
        return None

    if value_format is None:
        # cancel as no format is specified
        return value

    if isinstance(value_format, str):
        # format using a format-string
        return format(value, value_format)

    if callable(value_format):
        # format using a user defined function
        return value_format(value)

    # any other case means an error
    raise ValueError(f"Unsupported value format: {type(value_format)}. Expected: {FormatOptions}.")


def create_args_details(args: dict[str, Any], args_format: FormatOptions | dict[str, FormatOptions]) -> dict[str, Any]:
    if args_format is None:
        # cancel as no format is specified
        return {}

    if not args:
        # cancel as there's nothing to format
        return {}

    if isinstance(args_format, dict):
        # format each arg individually
        return {key: multi_format(args.get(key, None), args_format[key]) for key in args_format}
    else:
        # format all args with common format
        return {key: multi_format(args.get(key, None), args_format) for key in args}


def create_result_details(result: Any | None, result_format: FormatOptions | dict[str, FormatOptions]) -> dict[str, Any]:
    if result_format is None:
        return {}

    if result is None:
        return {}

    if isinstance(result_format, dict):
        return {key: multi_format(result, result_format[key]) for key in result_format}
    else:
        return {"value": multi_format(result, result_format)}


class ActivityComplete(Exception):
    pass


class LogError(Exception):
    pass


class Logger:

    def __init__(self, module: Optional[str], activity: str, parent: Optional["Logger"] = None):
        self.id = uuid.uuid4()
        self.module = module
        self.activity = activity
        self.parent = parent
        self.depth = sum(1 for _ in self)
        self._start = timer()
        self._logger = logging.getLogger(f"{module}.{activity}")
        self._traces: set[str] = set()

    @property
    def elapsed(self) -> float:
        return timer() - self._start

    @property
    def initial(self) -> "_Initial":
        return Logger._Initial(self)

    @property
    def unique(self) -> "_Unique":
        return Logger._Unique(self)

    @property
    def active(self) -> "_Active":
        return Logger._Active(self)

    @property
    def final(self) -> "_Final":
        return Logger._Final(self)

    def log_trace(
            self,
            name: Optional[str],
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None,
            level: int = logging.DEBUG,
            track_as: Optional[str] = None,
            **kwargs
    ):
        """Allows to log any other trace by specifying a custom name."""

        if kwargs.get("ignore_if_logged", False) and "final" in self._traces:
            return

        self._assure_trace_order(track_as)
        self._logger.setLevel(level)

        trace = name or inspect.stack()[1][3]
        trace = re.sub("^log_", "", trace, flags=re.IGNORECASE)  # remove the 'log_' prefix

        record_actions = [
            functools.partial(_set_module_name, name=self.module),
            functools.partial(_set_func_name, name=self.activity),
        ]

        extra = {
            "parent_id": self.parent.id if self.parent else None,
            "unique_id": self.id,
            "subject": self.module,
            "activity": self.activity,
            "trace": trace,
            "elapsed": self.elapsed,
            "details": (details or {}),
            "attachment": attachment,
            "_depth": self.depth
        }

        with _use_custom_log_record_factory(*record_actions):
            self._logger.log(level=self._logger.level, msg=message, exc_info=kwargs.get("exc_info", None), extra=extra)

    def _assure_trace_order(self, trace: Optional[str]):
        if not trace:
            return

        if "final" in self._traces:
            raise LogError(f"You cannot log any more traces.")

        if trace in self._traces:
            raise LogError(f"You can log '{trace}' only once.")

        if trace != "initial" and "initial" not in self._traces:
            raise LogError(f"You need to log an initial trace first.")

        self._traces.add(trace)

    def __iter__(self):
        current = self
        while current:
            yield current
            current = current.parent

    class _Initial:
        def __init__(self, logger: "Logger"):
            self._logger = logger

        def log_begin(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
            self._logger.log_trace(None, message, details, attachment, logging.INFO, track_as="initial")

    class _Unique:
        def __init__(self, logger: "Logger"):
            self._logger = logger

        def log_args(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
            self._logger.log_trace(None, message, details, attachment, logging.DEBUG, track_as="args")

        def log_result(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
            self._logger.log_trace(None, message, details, attachment, logging.DEBUG, track_as="result")

    class _Active:
        def __init__(self, logger: "Logger"):
            self._logger = logger

        def log_info(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
            self._logger.log_trace(None, message, details, attachment, logging.DEBUG)

        def log_item(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
            self._logger.log_trace(None, message, details, attachment, logging.DEBUG)

        def log_omit(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
            self._logger.log_trace(None, message, details, attachment, logging.DEBUG)

        def log_metric(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
            self._logger.log_trace(None, message, details, attachment, logging.DEBUG)

    class _Final:
        def __init__(self, logger: "Logger"):
            self._logger = logger

        def log_noop(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
            self._logger.log_trace(None, message, details, attachment, logging.INFO, track_as="final")

        def log_abort(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None) -> None:
            self._logger.log_trace(None, message, details, attachment, logging.INFO, track_as="final")

        def log_end(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None, **kwargs) -> None:
            self._logger.log_trace(None, message, details, attachment, logging.INFO, track_as="final", **kwargs)

        def log_error(self, message: Optional[str] = None, details: Optional[dict[str, Any]] = None, attachment: Optional[Any] = None, **kwargs) -> None:
            # process the exception only if it's not Failure
            exc_cls, exc, exc_tb = sys.exc_info()
            if all((exc_cls, exc, exc_tb)):
                # the first 3 frames are the decorator traces; let's get rid of them
                while exc_tb.tb_next:
                    exc_tb = exc_tb.tb_next
                self._logger.log_trace(None, message, details, attachment, logging.ERROR, track_as="final", exc_info=(exc_cls, exc, exc_tb), **kwargs)
            else:
                self._logger.log_trace(None, message, details, attachment, logging.ERROR, track_as="final", **kwargs)


@contextlib.contextmanager
def begin_activity(
        module: Optional[str],
        name: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        attachment: Optional[Any] = None
) -> ContextManager[Logger]:
    """Begins a new activity context."""
    logger = Logger(module, name, _scope.get())
    token = _scope.set(logger)
    try:
        logger.initial.log_begin(message, details, attachment)
        yield logger
        logger.final.log_end(ignore_if_logged=True)
    except Exception as e:  # noqa
        logger.final.log_error(message="Unhandled exception has occurred.", ignore_if_logged=True)
        raise
    finally:
        _scope.reset(token)


def telemetry(
        include_args: bool | FormatOptions | dict[str, FormatOptions] = False,
        include_result: bool | FormatOptions | dict[str, FormatOptions] = False,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        attachment: Optional[Any] = None,
        override: bool = False
):
    """Provides telemetry for the decorated function."""

    def raw(value: TValue) -> TValue:
        return value

    args_format: FormatOptions | dict[str, FormatOptions] = None
    if include_args:
        args_format = raw if isinstance(include_args, bool) else include_args

    result_format: FormatOptions | dict[str, FormatOptions] = None
    if include_result:
        result_format = raw if isinstance(include_result, bool) else include_result

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
                with begin_activity(module_name, scope_name, message=message, details=details or {}, attachment=attachment) as logger:
                    args_details = create_args_details(params(*decoratee_args, **decoratee_kwargs), args_format)
                    if include_args and args_details:
                        logger.unique.log_args(details=args_details)
                    inject_logger(logger, decoratee_kwargs)
                    result = await decoratee(*decoratee_args, **decoratee_kwargs)
                    result_details = create_result_details(result, result_format)
                    if include_result and result_details:
                        logger.unique.log_result(details=result_details)
                    logger.final.log_end(ignore_if_logged=True)
                    return result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

        else:
            @functools.wraps(decoratee)
            def decorator(*decoratee_args, **decoratee_kwargs):
                with begin_activity(module_name, scope_name, message=message, details=details or {}, attachment=attachment) as logger:
                    args_details = create_args_details(params(*decoratee_args, **decoratee_kwargs), args_format) if include_args else {}
                    if args_details:
                        logger.unique.log_args(details=args_details)
                    inject_logger(logger, decoratee_kwargs)
                    result = decoratee(*decoratee_args, **decoratee_kwargs)
                    result_details = create_result_details(result, result_format) if include_result else {}
                    if result_details:
                        logger.unique.log_result(details=result_details)
                    logger.final.log_end(ignore_if_logged=True)
                    return result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

    return factory


@contextlib.contextmanager
def _use_custom_log_record_factory(*actions: Callable[[logging.LogRecord], None]) -> ContextManager[None]:
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


def _set_func_name(record: logging.LogRecord, name: str):
    record.funcName = name


def _set_module_name(record: logging.LogRecord, name: str):
    record.module = name
