import sys
import logging
import inspect
import functools
import json
import asyncio
import uuid
import contextvars
import contextlib
# noinspection PyUnresolvedReferences
import layers
from typing import Dict, Callable, Any, Protocol, Optional, Self
from timeit import default_timer as timer
from datetime import datetime, date

_scope = contextvars.ContextVar("_scope", default=None)


class PieceOfWorkScope(Protocol):
    parent: Self
    id: uuid.UUID
    elapsed: float

    def running(self, **kwargs):
        ...

    def canceled(self, **kwargs):
        ...


class SerializeDetails(Protocol):
    def __call__(self, **kwargs) -> str | None: ...


class DefaultSerializeDetails(SerializeDetails):
    def __call__(self, **kwargs) -> str | None:
        return json.dumps(kwargs, sort_keys=True, allow_nan=False, cls=_JsonDateTimeEncoder) if kwargs else None


class PieceOfWork:
    serialize_details: SerializeDetails = DefaultSerializeDetails()

    def __init__(self, module: Optional[str], name: str, attachment: Any = None, parent: PieceOfWorkScope = None):
        self.id = uuid.uuid4()
        self.module = module
        self.name = name
        self.attachment = attachment
        self.parent = parent
        self._start = 0
        self._finalized = False
        self._logger = logging.getLogger(f"{module}.{name}")

    @property
    def elapsed(self) -> float:
        return round(timer() - self._start, 3)

    def started(self, **kwargs):
        self._start = timer()
        self._log(**kwargs)

    def running(self, **kwargs):
        self._log(**kwargs)

    def canceled(self, **kwargs):
        self._log(**kwargs)
        self._finalized = True

    def faulted(self, **kwargs):
        if not self._finalized:
            self._log(**kwargs)
            self._finalized = True

    def completed(self, **kwargs):
        if not self._finalized:
            self._log(**kwargs)
            self._finalized = True

    def _log(self, **kwargs):
        # kwargs["depth"] = sum(1 for _ in self)
        status = inspect.stack()[1][3]
        details = PieceOfWork.serialize_details(**kwargs)
        with _create_log_record(
                functools.partial(_set_module_name, name=self.module),
                functools.partial(_set_func_name, name=self.name)
        ):
            # Exceptions must be logged with the exception method or otherwise the exception will be missing.
            log = self._logger.exception if all(sys.exc_info()) else self._logger.info
            log(None, extra={
                "nodeId": self.id,
                "prevId": self.parent.id if self.parent else None,
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
def local(name: str, details: Dict | None = None, attachment: Any = None) -> PieceOfWorkScope:
    work = PieceOfWork(None, name, attachment, _scope.get())
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


def telemetry(*args, **kwargs):
    """Provides flow telemetry for the decorated function. Use named args to provide more static data."""

    for a in args:
        if callable(a):
            a(kwargs)

    def factory(decoratee):
        @contextlib.contextmanager
        def _context() -> PieceOfWork:
            work = PieceOfWork(
                module=inspect.getmodule(decoratee).__name__,
                name=decoratee.__name__,
                attachment=kwargs.pop("attachment", None),
                parent=_scope.get()
            )

            token = _scope.set(work)
            try:
                work.started(**kwargs)
                yield work
                work.completed()
            except Exception:
                work.faulted()
                raise
            finally:
                _scope.reset(token)

        def inject_scope(u: PieceOfWork, d: Dict):
            """ Injects the PieceOfWorkScope if required. """
            for n, t in inspect.getfullargspec(decoratee).annotations.items():
                if t is PieceOfWorkScope:
                    d[n] = u

        if asyncio.iscoroutinefunction(decoratee):
            @functools.wraps(decoratee)
            async def decorator(*decoratee_args, **decoratee_kwargs):
                with _context() as unit_of_work:
                    inject_scope(unit_of_work, decoratee_kwargs)
                    return await decoratee(*decoratee_args, **decoratee_kwargs)
        else:
            @functools.wraps(decoratee)
            def decorator(*decoratee_args, **decoratee_kwargs):
                with _context() as unit_of_work:
                    inject_scope(unit_of_work, decoratee_kwargs)
                    return decoratee(*decoratee_args, **decoratee_kwargs)

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
