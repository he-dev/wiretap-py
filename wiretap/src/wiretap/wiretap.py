import os
import sys
import logging
import inspect
import functools
import json
import asyncio
import uuid
import contextvars
import contextlib
from typing import Dict, Callable, Any, Protocol, Optional
from timeit import default_timer as timer
from datetime import datetime, date

_scope = contextvars.ContextVar("_scope", default=None)


class MultiFormatter(logging.Formatter):

    def __new__(cls, **kwargs):
        instance = super().__new__(cls)
        setattr(instance, "values", [])
        return instance

    def format(self, record: logging.LogRecord) -> str:
        # record.__dict__["instance"] = self.instance
        record.levelname = record.levelname.lower()
        record.values = self.values
        self._style._fmt = self.wiretap if hasattr(record, "status") else self.classic
        return super().format(record)


# @runtime_checkable
# class LoggerContext(Protocol):
#     parent: Any
#     id: uuid.UUID
#     elapsed: float
#
#     def running(self, **kwargs):
#         ...
#
#     def canceled(self, **kwargs):
#         ...


class Hierarchy(Protocol):
    parent: Any


class SerializeDetails(Protocol):
    def __call__(self, **kwargs) -> str | None: ...


class DefaultSerializeDetails(SerializeDetails):
    def __call__(self, **kwargs) -> str | None:
        return json.dumps(kwargs, sort_keys=True, allow_nan=False, cls=_JsonDateTimeEncoder) if kwargs else None


class Logger:
    serialize_details: SerializeDetails = DefaultSerializeDetails()

    def __init__(self, module: Optional[str], scope: str, attachment: Optional[Any] = None, parent: Optional[Hierarchy] = None):
        self.id = uuid.uuid4()
        self.module = module
        self.scope = scope
        self.attachment = attachment
        self.parent = parent
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
        if self._finalized:
            return

        self._logger.setLevel(logging.INFO)
        self._log(**kwargs)
        self._finalized = True

    def canceled(self, **kwargs):
        if self._finalized:
            return

        self._logger.setLevel(logging.WARNING)
        self._log(**kwargs)
        self._finalized = True

    def faulted(self, **kwargs):
        if self._finalized:
            return

        self._logger.setLevel(logging.ERROR)
        self._log(**kwargs)
        self._finalized = True

    def _log(self, **kwargs):
        # kwargs["depth"] = sum(1 for _ in self)
        status = inspect.stack()[1][3]
        details = Logger.serialize_details(**kwargs)
        with _create_log_record(
                functools.partial(_set_module_name, name=self.module),
                functools.partial(_set_func_name, name=self.scope)
        ):
            # Exceptions must be logged with the exception method or otherwise the exception will be missing.
            is_error = all(sys.exc_info()) and sys.exc_info()[0] is not ContinuationError
            self._logger.log(level=self._logger.level, msg=None, exc_info=is_error, extra={
                "parent": self.parent.id if self.parent else None,
                "node": self.id,
                "status": status,
                "elapsed": self.elapsed,
                "details": details,
                "attachment": self.attachment
            })

    def __iter__(self):
        current = self
        while current:
            yield current
            current = current.parent


@contextlib.contextmanager
def local(name: str, details: Dict | None = None, attachment: Any = None) -> Logger:
    work = Logger(None, name, attachment, _scope.get())
    token = _scope.set(work)
    try:
        work.started(**details if details else dict())
        yield work
        work.completed()
    except Exception:
        work.faulted()
        raise
    finally:
        _scope.reset(token)


class AttachDetails(Protocol):
    def __call__(self, details: Dict[str, Any]) -> None: ...


class OnStarted(Protocol):
    """Allows you to create details from function arguments."""

    def __call__(self, kwargs: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...


class OnCompleted(Protocol):
    """Allows you to create details from function result."""

    def __call__(self, result: Any) -> Optional[Dict[str, Any]]: ...


class ContinuationError(Exception):
    """Raise this error to gracefully handle a cancellation."""
    def __new__(cls, *args, **details) -> Any:
        instance = super().__new__(cls)
        instance.details = details | dict(reason=args[0])
        if len(args) > 1:
            instance.result = args[1]
        return instance

    def __init__(self, message: str, result: Optional[Any] = None, **details):
        super().__init__(message)


def telemetry(on_started: Optional[OnStarted] = None, on_completed: Optional[OnCompleted] = None, **kwargs):
    """Provides flow telemetry for the decorated function. Use named args to provide more static data."""

    on_started = on_started or (lambda _: {})
    on_completed = on_completed or (lambda _: {})

    def factory(decoratee):
        @contextlib.contextmanager
        def logger_scope() -> Logger:
            logger = Logger(
                module=inspect.getmodule(decoratee).__name__,
                scope=decoratee.__name__,
                attachment=kwargs.pop("attachment", None),
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

        if asyncio.iscoroutinefunction(decoratee):
            @functools.wraps(decoratee)
            async def decorator(*decoratee_args, **decoratee_kwargs):
                with logger_scope() as scope:
                    inject_logger(scope, decoratee_kwargs)
                    scope.started(**on_started(params(*decoratee_args, **decoratee_kwargs)))
                    try:
                        result = await decoratee(*decoratee_args, **decoratee_kwargs)
                        scope.completed(**on_completed(result))
                        return result
                    except ContinuationError as e:
                        if hasattr(e, "result"):
                            scope.canceled(**(on_completed(e.result) | e.details))
                            return e.result
                        else:
                            scope.canceled(**e.details)
        else:
            @functools.wraps(decoratee)
            def decorator(*decoratee_args, **decoratee_kwargs):
                with logger_scope() as scope:
                    inject_logger(scope, decoratee_kwargs)
                    scope.started(**on_started(params(*decoratee_args, **decoratee_kwargs)))
                    try:
                        result = decoratee(*decoratee_args, **decoratee_kwargs)
                        scope.completed(**on_completed(result))
                        return result
                    except ContinuationError as e:
                        if hasattr(e, "result"):
                            scope.canceled(**(on_completed(e.result) | e.details))
                            return e.result
                        else:
                            scope.canceled(**e.details)

        decorator.__signature__ = inspect.signature(decoratee)
        return decorator

    return factory


@contextlib.contextmanager
def _create_log_record(*actions: Callable[[logging.LogRecord], None]):
    default = logging.getLogRecordFactory()

    def custom(*args, **kwargs):
        record = default(*args, **kwargs)

        if record.exc_info:
            record.exc_text = logging.Formatter().formatException(record.exc_info)

        for action in actions:
            action(record)
        return record

    logging.setLogRecordFactory(custom)
    yield
    logging.setLogRecordFactory(default)


def _set_func_name(record: logging.LogRecord, name: str):
    record.funcName = name


def _set_module_name(record: logging.LogRecord, name: str):
    record.module = name


class _JsonDateTimeEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, (date, datetime)):
            return o.isoformat()
