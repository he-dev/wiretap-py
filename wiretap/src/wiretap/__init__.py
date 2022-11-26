import sys
import logging
import inspect
import functools
import json
import asyncio
import uuid
import contextvars
import contextlib
import layers
from typing import Dict, Callable, Any, Protocol, List
from timeit import default_timer as timer
from datetime import datetime, date

_scope = contextvars.ContextVar("_scope", default=None)


def telemetry(*args, **kwargs):
    """Provides flow telemetry for the decorated function. Use named args to provide more static data."""

    for a in args:
        if callable(a):
            a(kwargs)

    def factory(decoratee):
        unit_of_work = UnitOfWork(
            module=inspect.getmodule(decoratee).__name__,
            name=decoratee.__name__,
            extra=dict(**kwargs),
            parent=_scope.get()
        )
        _scope.set(unit_of_work)

        @contextlib.contextmanager
        def _context():
            try:
                unit_of_work.started()
                yield
                unit_of_work.completed()
            except:
                unit_of_work.faulted()
                raise
            finally:
                _scope.set(unit_of_work.parent)

        if asyncio.iscoroutinefunction(decoratee):
            @functools.wraps(decoratee)
            async def decorator(*decoratee_args, **decoratee_kwargs):
                with _context():
                    return await decoratee(*decoratee_args, **decoratee_kwargs)
        else:
            @functools.wraps(decoratee)
            def decorator(*decoratee_args, **decoratee_kwargs):
                with _context():
                    return decoratee(*decoratee_args, **decoratee_kwargs)

        return decorator

    return factory


class UnitOfWork:

    def __init__(self, module: str, name: str | None = None, extra: Dict | None = None, parent: Any = None):
        self._logger = logging.getLogger(f"{module}.{name}")
        self._module = module
        self._name = name
        self._extra = extra or {}
        self._start = 0
        self._is_cancelled = False
        self.correlation_id = uuid.uuid4().hex
        self.parent = parent

    @property
    def elapsed(self) -> float:
        return round(round(timer(), 3) - round(self._start, 3), 3)

    def started(self, **kwargs):
        self._start = timer()
        self._log(**kwargs)

    def running(self, **kwargs):
        self._log(**kwargs)

    def canceled(self, **kwargs):
        self._is_cancelled = True
        self._log(**kwargs)

    def faulted(self, **kwargs):
        if not self._is_cancelled:
            self._log(**kwargs)

    def completed(self, **kwargs):
        if not self._is_cancelled:
            self._log(**kwargs)

    def _log(self, **kwargs):
        kwargs["elapsed"] = self.elapsed
        status = inspect.stack()[1][3]
        # Use telemetry extra only for "started".
        extra = json.dumps(dict(**self._extra if status == "started" else {}, **kwargs), sort_keys=True, allow_nan=False, cls=_JsonDateTimeEncoder)
        with _update_log_record(
                functools.partial(_set_module_name, name=self._module),
                functools.partial(_set_func_name, name=self._name)
        ):
            log = self._logger.exception if all(sys.exc_info()) else self._logger.info
            log(None, extra={"status": status, "correlation": [x.correlation_id for x in self], "extra": extra})

    def __iter__(self):
        current = self
        while current:
            yield current
            current = current.parent


class UnitOfWorkScope:

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    @property
    def elapsed(self) -> float:
        return self._uow.elapsed

    def running(self, **kwargs):
        self._uow.running(**kwargs)

    def canceled(self, **kwargs):
        self._uow.canceled(**kwargs)


def scope() -> UnitOfWorkScope:
    return UnitOfWorkScope(_scope.get())


def elapsed() -> float:
    return scope().elapsed


def running(**kwargs) -> None:
    return scope().running(**kwargs)


def canceled(**kwargs) -> None:
    return scope().canceled(**kwargs)


@contextlib.contextmanager
def _update_log_record(*actions: Callable[[logging.LogRecord], None]):
    default = logging.getLogRecordFactory()

    def custom(*args, **kwargs):
        record = default(*args, **kwargs)
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
