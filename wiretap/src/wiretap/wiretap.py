import sys
import asyncio
import contextlib
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
from typing import Dict, Callable, Any, Protocol, Optional, Iterator

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
    "wiretap": "{asctime}.{msecs:.0f} [{indent}] {levelname} | {module}.{funcName} | {status} | {elapsed} | {details} | [{parent}/{node}] | {attachment}",
}


class MultiFormatter(logging.Formatter):
    formats: Dict[str, str] = DEFAULT_FORMATS
    indent: str = "."
    values: Optional[Dict[str, Any]] = None
    serialize_details: SerializeDetails = SerializeDetailsToJson()

    def format(self, record: logging.LogRecord) -> str:
        record.levelname = record.levelname.lower()
        record.values = self.values or {}

        if hasattr(record, "details") and isinstance(record.details, dict):
            record.indent = self.indent * record.details["depth"]
            record.details = self.serialize_details(record.details)

        self._style._fmt = self.formats["classic"]

        if hasattr(record, "status"):
            self._style._fmt = self.formats["wiretap"]

        if hasattr(record, "format"):
            self._style._fmt = record.format

        self.formats = DEFAULT_FORMATS | self.formats
        return super().format(record)


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
        return round(timer() - self._start, 3)

    def started(self, **kwargs):
        self._logger.setLevel(logging.INFO)
        self._start = timer()
        self._log(**kwargs)

    def running(self, **kwargs):
        self._logger.setLevel(logging.DEBUG)
        self._log(**kwargs)

    def completed(self, **kwargs):
        self._logger.setLevel(logging.INFO)
        self._log(**kwargs)

    def canceled(self, **kwargs):
        self._logger.setLevel(logging.WARNING)
        self._log(**kwargs)

    def faulted(self, **kwargs):
        self._logger.setLevel(logging.ERROR)
        self._log(**kwargs)

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
            # Exceptions must be logged with the exception method or otherwise the exception will be missing.
            is_error = all(sys.exc_info()) and sys.exc_info()[0] is not CannotContinue
            self._logger.log(level=self._logger.level, msg=None, exc_info=is_error, extra={
                "parent": self.parent.id if self.parent else None,
                "node": self.id,
                "status": status,
                "elapsed": self.elapsed,
                "details": kwargs | {"depth": self.depth}
            })

        self._finalized = status in [self.completed.__name__, self.canceled.__name__, self.faulted.__name__]

    def __iter__(self):
        current = self
        while current:
            yield current
            current = current.parent


class AttachDetails(Protocol):
    def __call__(self, details: Dict[str, Any]) -> None: ...


class OnStarted(Protocol):
    """Allows you to create details from function arguments."""

    def __call__(self, kwargs: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...


class OnCompleted(Protocol):
    """Allows you to create details from function result."""

    def __call__(self, result: Any) -> Optional[Dict[str, Any]]: ...


class CannotContinue(Exception):
    """Raise this error to gracefully handle a cancellation."""

    details: Dict[str, Any] = dict()
    result: Optional[Any] = None

    def __new__(cls, reason: str, result: Optional[Any] = None, **details) -> "CannotContinue":
        instance = super().__new__(cls)
        details["reason"] = reason
        instance.details = details
        instance.result = result
        return instance

    def __init__(self, reason: str, result: Optional[Any] = None, **details):
        super().__init__(reason)


class ReturnValueMissing(Exception):

    def __init__(self, name: str):
        super().__init__(f"Function '{name}' expects a return value, but it wasn't provided.")


def telemetry(on_started: Optional[OnStarted] = lambda _: None, on_completed: Optional[OnCompleted] = lambda _: None, attachment: Optional[Any] = None):
    """Provides flow telemetry for the decorated function. Use named args to provide more static data."""

    def factory(decoratee):
        module = inspect.getmodule(decoratee)

        @contextlib.contextmanager
        def logger_scope() -> Iterator[Logger]:
            logger = Logger(
                module=module.__name__ if module else None,
                scope=decoratee.__name__,
                parent=_scope.get()
            )

            token = _scope.set(logger)
            try:
                yield logger
            except Exception:
                logger.faulted()
                raise
            finally:
                _scope.reset(token)

        def inject_logger(logger: Logger, d: Dict):
            """ Injects Logger if required. """
            for n, t in inspect.getfullargspec(decoratee).annotations.items():
                if t is Logger:
                    d[n] = logger

        def params(*decoratee_args, **decoratee_kwargs) -> Dict[str, Any]:
            # Zip arg names and their indexes up to the number of args of the decoratee_args.
            arg_pairs = zip(inspect.getfullargspec(decoratee).args, range(len(decoratee_args)))
            # Turn arg_pairs into a dictionary and combine it with decoratee_kwargs.
            return {t[0]: decoratee_args[t[1]] for t in arg_pairs} | decoratee_kwargs

        # returns = inspect.getfullargspec(decoratee).annotations.get("return", None) is not None

        if asyncio.iscoroutinefunction(decoratee):
            @functools.wraps(decoratee)
            async def decorator(*decoratee_args, **decoratee_kwargs):
                if attachment:
                    decoratee_kwargs["attachment"] = attachment
                with logger_scope() as scope:
                    inject_logger(scope, decoratee_kwargs)
                    scope.started(**on_started(params(*decoratee_args, **decoratee_kwargs)))
                    try:
                        result = await decoratee(*decoratee_args, **decoratee_kwargs)
                        scope.completed(**on_completed(result))
                        return result
                    except CannotContinue as e:
                        scope.canceled(**(on_completed(e.result) | e.details))
                        return e.result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

        else:
            @functools.wraps(decoratee)
            def decorator(*decoratee_args, **decoratee_kwargs):
                if attachment:
                    decoratee_kwargs["attachment"] = attachment
                with logger_scope() as scope:
                    inject_logger(scope, decoratee_kwargs)
                    scope.started(**on_started(params(*decoratee_args, **decoratee_kwargs)))
                    try:
                        result = decoratee(*decoratee_args, **decoratee_kwargs)
                        scope.completed(**on_completed(result))
                        return result
                    except CannotContinue as e:
                        scope.canceled(**(on_completed(e.result) | e.details))
                        return e.result

            decorator.__signature__ = inspect.signature(decoratee)
            return decorator

    return factory


@contextlib.contextmanager
def begin_telemetry(name: str, **kwargs) -> Iterator[Logger]:
    """Begins a new telemetry scope."""
    logger = Logger(None, name, _scope.get())
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
