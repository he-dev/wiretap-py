import sys
import logging
import inspect
from typing import Dict, Callable
from timeit import default_timer as timer

class UnitOfWork:
    logger: logging.Logger

    def __init__(self, logger: logging.Logger = None, name: str | None = None, extra: Dict | None = None):
        self._logger = logger or self.logger
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
        with CustomLogRecordFactoryScope(self._set_func_name):
            log = self._logger.exception if all(sys.exc_info()) else self._logger.info
            log(None, extra={"status": status, "extra": dict(**kwargs, **self._extra)})

    def _set_func_name(self, record: logging.LogRecord):
        record.funcName = self._name

    def __call__(self, decoratee):
        def decorator(*decoratee_args, **decoratee_kwargs):
            self._name = self._name or decoratee.__name__

            # Inject scope if required.
            for n, t in inspect.getfullargspec(decoratee).annotations.items():
                if t is UnitOfWorkScope:
                    decoratee_kwargs[n] = UnitOfWorkScope(self)

            with self:
                return decoratee(*decoratee_args, **decoratee_kwargs)

        return decorator

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


class CustomLogRecordFactoryScope:

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
