import sys
import logging
import inspect
import functools
import json
from typing import Dict, Callable, Any
from timeit import default_timer as timer
from datetime import datetime, date

PRESENTATION = {"layer": "PRESENTATION"}
APPLICATION = {"layer": "APPLICATION"}
BUSINESS = {"layer": "BUSINESS"}
PERSISTENCE = {"layer": "PERSISTENCE"}
DATABASE = {"layer": "DATABASE"}


def telemetry(**kwargs):
    """Provides flow telemetry for the decorated function. Use named args to provide more static data."""

    def factory(decoratee):
        @functools.wraps(decoratee)
        def decorator(*decoratee_args, **decoratee_kwargs):
            uow = UnitOfWork(inspect.getmodule(decoratee).__name__, decoratee.__name__, dict(**kwargs))

            # Inject scope if required.
            for n, t in inspect.getfullargspec(decoratee).annotations.items():
                if t is UnitOfWorkScope:
                    decoratee_kwargs[n] = UnitOfWorkScope(uow)

            with uow:
                return decoratee(*decoratee_args, **decoratee_kwargs)

        return decorator

    return factory


class UnitOfWork:

    def __init__(self, module: str, name: str | None = None, extra: Dict | None = None):
        self._logger = logging.getLogger(f"{module}.{name}")
        self._module = module
        self._name = name
        self._extra = extra or {}
        self._start = 0
        self._is_cancelled = False

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
        # Use local extra only for started.
        extra = json.dumps(dict(**self._extra if status == "started" else {}, **kwargs), sort_keys=True, allow_nan=False, cls=_JsonDateTimeEncoder)
        with _CustomLogRecordFactoryScope(self._set_module_name, self._set_func_name):
            log = self._logger.exception if all(sys.exc_info()) else self._logger.info
            log(None, extra={"status": status, "extra": extra})

    def _set_func_name(self, record: logging.LogRecord):
        record.funcName = self._name

    def _set_module_name(self, record: logging.LogRecord):
        record.module = self._module

    def __enter__(self):
        self.started()
        return UnitOfWorkScope(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        (self.faulted if exc_type else self.completed)()


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


class _CustomLogRecordFactoryScope:

    def __init__(self, *actions: Callable[[logging.LogRecord], None]):
        self._actions = actions

    def __enter__(self):
        self._default = logging.getLogRecordFactory()

        def custom(*args, **kwargs):
            record = self._default(*args, **kwargs)
            for action in self._actions:
                action(record)
            return record

        logging.setLogRecordFactory(custom)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self._default)


class _JsonDateTimeEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, (date, datetime)):
            return o.isoformat()
