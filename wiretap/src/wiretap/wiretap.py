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
from typing import Dict, Callable, Any, Protocol, Optional, Iterator, TypeVar

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


DEFAULT_FORMATS: Dict[str, str] = {
    "classic": "{asctime}.{msecs:.0f} | {levelname} | {module}.{funcName} | {message}",
    "wiretap": "{asctime}.{msecs:.0f} {indent} {levelname} | {module}.{funcName}: {status} | {elapsed:.3f}s | {details} | [{parent}/{node}] | {attachment}",
}


class MultiFormatter(logging.Formatter):
    formats: Dict[str, str | None] = {}
    indent: str = "."
    values: Optional[Dict[str, Any]] = None
    serialize_details: SerializeDetails = SerializeDetailsToJson()

    def format(self, record: logging.LogRecord) -> str:
        record.levelname = record.levelname.lower()

        for key in self.values or {}:
            record.__dict__[key] = self.values[key]

        if hasattr(record, "details") and isinstance(record.details, dict):
            record.indent = self.indent * record.details.pop("__depth__", 1)
            record.details = self.serialize_details(record.details)

        self._style._fmt = self.formats.get("classic", None) or DEFAULT_FORMATS["classic"]

        if hasattr(record, "status"):
            self._style._fmt = self.formats.get("wiretap", None) or DEFAULT_FORMATS["wiretap"]

        fallback = record.__dict__.pop("fallback", None)
        if fallback:
            self._style._fmt = fallback

        return super().format(record)


class OnStarted(Protocol):
    """Allows you to create details from function arguments."""

    def __call__(self, params: Dict[str, Any]) -> Dict[str, Any]: ...


class OnCompleted(Protocol):
    """Allows you to create details from function result."""

    def __call__(self, result: Optional[Any]) -> Dict[str, Any]: ...


class EmptyOnStarted:
    def __call__(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {}


class EmptyOnCompleted(OnCompleted):
    def __call__(self, result: Optional[Any]) -> Dict[str, Any]:
        return {}


def _format_detail(value: Any, formats: Optional[str | Callable[[Any], Any]]) -> Optional[Any]:
    if not value:
        return None

    if isinstance(value, enum.Enum):
        value = value.value

    if not formats:
        return value

    if isinstance(formats, str):
        return format(value, formats)

    if callable(formats):
        return formats(value)

    raise ValueError(f"Details format supports only [str | Callable[[Any], Any] not {type(formats)}")


class FormatStartDetails(OnStarted):

    def __init__(self, **details):
        """Formats function parameters. Each key corresponds to the same parameter. The value is can be [None | str | Callable[[Any], Any]."""
        self.details = details

    def __call__(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {key: _format_detail(params.get(key, None), self.details[key]) for key in self.details}


class FormatResultDetails(OnCompleted):

    def __init__(self, formats: Optional[str | Callable[[Any], Any]] = None, **details):
        """Formats function result.
        :param formats: Use this to specify how to format the "result".
        :param details: Use this to specify multiple keys or rename the "result" to something else.
        """
        self.formats = formats
        self.details = details

    def __call__(self, value: Optional[Any]) -> Dict[str, Any]:
        if not value:
            return dict(result=None)

        if self.formats:
            return dict(result=_format_detail(value, self.formats))

        if self.details:
            return {key: _format_detail(value, self.details[key]) for key in self.details}

        return dict(result=value)


TResult = TypeVar("TResult")


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

    def started(self, **details):
        self._logger.setLevel(logging.INFO)
        self._start = timer()
        self._log(**details)

    def running(self, **details):
        self._logger.setLevel(logging.DEBUG)
        self._log(**details)

    def completed(self, result: Optional[TResult] = None, details_factory: OnCompleted = EmptyOnCompleted(), **details) -> Optional[TResult]:
        self._logger.setLevel(logging.INFO)
        self._log(**(details_factory(result) | details))
        return result

    def canceled(self, result: Optional[TResult] = None, details_factory: OnCompleted = EmptyOnCompleted(), **details) -> Optional[TResult]:
        self._logger.setLevel(logging.WARNING)
        self._log(**(details_factory(result) | details))
        return result

    def faulted(self, result: Optional[TResult] = None, details_factory: OnCompleted = EmptyOnCompleted(), **details) -> Optional[TResult]:
        self._logger.setLevel(logging.ERROR)
        self._log(**(details_factory(result) | details))
        return result

    def _log(self, **kwargs):
        if self._finalized:
            return

        status = inspect.stack()[1][3]
        with _use_custom_log_record_factory(
                _set_exc_text,
                functools.partial(_set_module_name, name=self.module),
                functools.partial(_set_func_name, name=self.scope),
                functools.partial(_set_attachment, value=kwargs.pop("attachment", None)),
        ):
            exc_info = all(sys.exc_info()) and status in [self.faulted.__name__]  # Dump the exception only when faulted.
            self._logger.log(level=self._logger.level, msg=None, exc_info=exc_info, extra={
                "parent": self.parent.id if self.parent else None,
                "node": self.id,
                "status": status,
                "elapsed": self.elapsed,
                "details": kwargs | {"__depth__": self.depth}
            })

        self._finalized = status in [self.completed.__name__, self.canceled.__name__, self.faulted.__name__]

    def __iter__(self):
        current = self
        while current:
            yield current
            current = current.parent


@contextlib.contextmanager
def collect(module: Optional[str], name: str, **kwargs) -> Iterator[Logger]:
    """Begins a new telemetry scope."""
    logger = Logger(module, name, _scope.get())
    token = _scope.set(logger)
    try:
        logger.started(**kwargs)
        yield logger
        logger.completed()
    except:  # noqa
        logger.faulted()
        raise
    finally:
        _scope.reset(token)


def include_args(**details):
    """Includes the specified arguments in the `started` status."""

    def factory(decoratee):
        if asyncio.iscoroutinefunction(decoratee):
            pass
        else:
            @functools.wraps(decoratee)
            def decorator(*decoratee_args, **decoratee_kwargs):
                decoratee_kwargs[f"__{include_args.__name__}__"] = FormatStartDetails(**details)
                return decoratee(*decoratee_args, **decoratee_kwargs)

            return decorator

    return factory


def include_result(formats: Optional[str | Callable[[Any], Any]] = None, **details):
    """Includes the specified arguments in the `completed` status."""

    def factory(decoratee):
        if asyncio.iscoroutinefunction(decoratee):
            pass
        else:
            @functools.wraps(decoratee)
            def decorator(*decoratee_args, **decoratee_kwargs):
                decoratee_kwargs[f"__{include_result.__name__}__"] = FormatResultDetails(formats, **details)
                return decoratee(*decoratee_args, **decoratee_kwargs)

            return decorator

    return factory


@dataclasses.dataclass
class _TelemetryOptions:
    args_func: OnStarted
    result_func: OnCompleted


def collect_telemetry(**kwargs):
    """Provides telemetry for the decorated function."""

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

        def pop_options(kwargs: dict[str, Any]) -> _TelemetryOptions:
            # start_attachment_value = decoratee_kwargs.pop(start_attachment.__name__, None)
            return _TelemetryOptions(
                args_func=kwargs.pop(f"__{include_args.__name__}__", EmptyOnStarted()),
                result_func=kwargs.pop(f"__{include_result.__name__}__", EmptyOnCompleted())
            )

        if asyncio.iscoroutinefunction(decoratee):
            @functools.wraps(decoratee)
            async def decorator(*decoratee_args, **decoratee_kwargs):
                start_details = on_started(params(*decoratee_args, **decoratee_kwargs)) | dict(attachment=attachment)
                with collect(module_name, scope_name, **start_details) as scope:
                    inject_logger(scope, decoratee_kwargs)
                    scope.started(**(on_started(params(*decoratee_args, **decoratee_kwargs)) or {}))
                    result = await decoratee(*decoratee_args, **decoratee_kwargs)
                    return scope.completed(result, on_completed)

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

        else:
            @functools.wraps(decoratee)
            def decorator(*decoratee_args, **decoratee_kwargs):
                options = pop_options(decoratee_kwargs)
                details = options.args_func(params(*decoratee_args, **decoratee_kwargs)) | dict(attachment=None)
                with collect(module_name, scope_name, **details) as scope:
                    inject_logger(scope, decoratee_kwargs)
                    result = decoratee(*decoratee_args, **decoratee_kwargs)
                    return scope.completed(result, options.result_func)

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


def _set_exc_text(record: logging.LogRecord):
    if record.exc_info:
        record.exc_text = logging.Formatter().formatException(record.exc_info)


def _set_attachment(record: logging.LogRecord, value: Optional[Any]):
    record.attachment = record.exc_text or value
