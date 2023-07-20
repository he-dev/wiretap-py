import asyncio
import contextlib
import dataclasses
import enum
import functools
import inspect
import json
import logging
import sys
import uuid
from collections.abc import Generator
from contextvars import ContextVar
from datetime import datetime, date
from timeit import default_timer as timer
from types import TracebackType
from typing import Dict, Callable, Any, Protocol, Optional, Iterator, TypeVar, TypeAlias

FormatOptions: TypeAlias = str | Callable[[Any], Any] | None
TValue = TypeVar("TValue")

DEFAULT_FORMATS: Dict[str, str] = {
    "classic": "{asctime}.{msecs:.0f} | {levelname} | {module}.{funcName} | {message}",
    "wiretap": "{asctime}.{msecs:.0f} {indent} {levelname} | {module}.{funcName} | {status} | {elapsed:.3f}s | {message} | {details} | node://{parent}/{node} | {attachment}",
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

        if hasattr(record, "status"):
            self._style._fmt = self.formats["wiretap"] if "wiretap" in self.formats else DEFAULT_FORMATS["wiretap"]
        else:
            self._style._fmt = self.formats["classic"] if "classic" in self.formats else DEFAULT_FORMATS["classic"]

        return super().format(record)


def raw(value: TValue) -> TValue:
    return value


def multi_format(value: Any, value_format: FormatOptions) -> Optional[Any]:
    if value is None:
        return None

    if value_format is None:
        return value

    if isinstance(value_format, str):
        return format(value, value_format)

    if callable(value_format):
        return value_format(value)

    raise ValueError(f"Unsupported details format: {type(value_format)}. Expected: {FormatOptions}.")


def create_args_details(args: dict[str, Any], args_format: FormatOptions | dict[str, FormatOptions]) -> dict[str, Any]:
    if args_format is None:
        return {}

    if not args:
        return {}

    if isinstance(args_format, dict):
        return {"args": {key: multi_format(args.get(key, None), args_format[key]) for key in args_format}}

    return {"args": {key: multi_format(args.get(key, None), args_format) for key in args}}


def create_result_details(result: Any | None, result_format: FormatOptions | dict[str, FormatOptions]) -> dict[str, Any]:
    if result_format is None:
        return {}

    if result is None:
        return {}

    if isinstance(result_format, dict):
        return {"result": {key: multi_format(result, result_format[key]) for key in result_format}}

    return {"result": multi_format(result, result_format)}


class Logger:

    def __init__(self, module: Optional[str], scope: str, parent: Optional["Logger"] = None):
        self.id = uuid.uuid4()
        self.module = module
        self.scope = scope
        self.parent = parent
        self.depth = sum(1 for _ in self)
        self._start = timer()
        self._finalized = False
        self._logger = logging.getLogger(f"{module}.{scope}")

    @property
    def elapsed(self) -> float:
        return timer() - self._start

    def started(
            self,
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None
    ):
        self._logger.setLevel(logging.INFO)
        self._start = timer()
        self._log(message, details, attachment)

    def running(
            self,
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None
    ):
        self._logger.setLevel(logging.DEBUG)
        self._log(message, details, attachment)

    def completed(
            self,
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None,
            result: Optional[TValue] = None,
            result_format: FormatOptions | dict[str, FormatOptions] = None
    ) -> Optional[TValue]:
        self._logger.setLevel(logging.INFO)
        self._log(message, details, attachment, result, result_format)
        return result

    def canceled(
            self,
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None,
            result: Optional[TValue] = None,
            result_format: FormatOptions | dict[str, FormatOptions] = None
    ) -> Optional[TValue]:
        self._logger.setLevel(logging.WARNING)
        self._log(message, details, attachment, result, result_format)
        return result

    def failed(
            self,
            message: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            attachment: Optional[Any] = None,
            result: Optional[TValue] = None,
            result_format: FormatOptions | dict[str, FormatOptions] = None
    ) -> Optional[TValue]:
        self._logger.setLevel(logging.ERROR)

        # process the exception only if it's not Failure
        exc_cls, exc, exc_tb = sys.exc_info()
        if exc and exc_cls is not Failure:
            # the first 3 frames are the decorator traces; let's get rid of them
            for _ in range(3):
                # in case there aren't that many frames
                if exc_tb.tb_next:
                    exc_tb = exc_tb.tb_next
                else:
                    break
            self._log(message, details, attachment, result, result_format, (exc_cls, exc, exc_tb))
        else:
            self._log(message, details, attachment, result, result_format)

        return result

    def _log(
            self,
            message: Optional[str],
            details: Optional[dict[str, Any]],
            attachment: Optional[Any],
            result: Optional[TValue] = None,
            result_format: FormatOptions | dict[str, FormatOptions] = None,
            exc_info: Optional[tuple[type[BaseException], BaseException, TracebackType | None]] = None
    ):
        if self._finalized:
            return

        details = (details or {}) | create_result_details(result, result_format)

        status = inspect.stack()[1][3]
        with _use_custom_log_record_factory(
                functools.partial(_set_module_name, name=self.module),
                functools.partial(_set_func_name, name=self.scope),
        ):
            self._logger.log(level=self._logger.level, msg=message, exc_info=exc_info, extra={
                "parent": self.parent.id if self.parent else None,
                "node": self.id,
                "status": status,
                "elapsed": self.elapsed,
                "details": details or {},
                "attachment": attachment,
                "_depth": self.depth
            })

        self._finalized = status in [
            self.completed.__name__,
            self.canceled.__name__,
            self.failed.__name__
        ]

    def __iter__(self):
        current = self
        while current:
            yield current
            current = current.parent


# Helps to prevent logging the same exception multiple times.
class Failure(Exception):
    pass


@contextlib.contextmanager
def telemetry_scope(
        module: Optional[str],
        name: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        attachment: Optional[Any] = None
) -> Iterator[Logger]:
    """Begins a new telemetry scope."""
    logger = Logger(module, name, _scope.get())
    token = _scope.set(logger)
    try:
        logger.started(message, details, attachment)
        yield logger
        logger.completed()
    except Failure:
        logger.failed()
        raise
    except Exception as e:  # noqa
        logger.failed()
        raise Failure from e  # wrap the original exception in Failure to keep failing and prevent logging it multiple times
    finally:
        _scope.reset(token)


class NoValue:
    pass


class Cancellation(Exception):
    def __init__(self, message: str, result: TValue | NoValue = NoValue()):
        super().__init__(message)
        self.result = result


def telemetry(
        include_args: bool | FormatOptions | dict[str, FormatOptions] = False,
        include_result: bool | FormatOptions | dict[str, FormatOptions] = False,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        attachment: Optional[Any] = None
):
    """Provides telemetry for the decorated function."""

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
                details_ = create_args_details(params(*decoratee_args, **decoratee_kwargs), args_format) | (details or {})
                with telemetry_scope(module_name, scope_name, message=message, details=details_, attachment=attachment) as scope:
                    inject_logger(scope, decoratee_kwargs)
                    result = await decoratee(*decoratee_args, **decoratee_kwargs)
                    return scope.completed(result=result, result_format=result_format)

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

        else:
            @functools.wraps(decoratee)
            def decorator(*decoratee_args, **decoratee_kwargs):
                details_ = create_args_details(params(*decoratee_args, **decoratee_kwargs), args_format) | (details or {})
                with telemetry_scope(module_name, scope_name, message=message, details=details_, attachment=attachment) as scope:
                    inject_logger(scope, decoratee_kwargs)
                    try:
                        result = decoratee(*decoratee_args, **decoratee_kwargs)
                        return scope.completed(result=result, result_format=result_format)
                    except Cancellation as e:
                        return scope.canceled(result=e.result if type(e.result) is not NoValue else None, message=str(e), result_format="")

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

    return factory


@contextlib.contextmanager
def _use_custom_log_record_factory(*actions: Callable[[logging.LogRecord], None]) -> Generator[None, None, None]:
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
