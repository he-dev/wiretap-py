from __future__ import annotations

import abc
import inspect
import logging
import secrets
from contextlib import contextmanager
from contextvars import ContextVar  # noqa: built-in module
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import islice
from typing import Any, Iterator, ClassVar, runtime_checkable, Protocol, Callable, Annotated, get_type_hints

from wiretap.meta import trim_path
from wiretap.util.path_of import PathOf
from wiretap.util.stopwatch import Stopwatch

# util: Internal logger.
_logger = logging.getLogger("wiretap")


@dataclass(frozen=True)
class StateItem:
    # core: When True, the value cascades to all activities down the stack.
    cascade: bool = field(default=False)
    default_value: Any = field(default=None)


@dataclass(frozen=True)
class MessagePart:
    label: str | None = None


# core: Reads and caches annotated fields for status classes because they use [Annotated] fields.
@lru_cache(maxsize=None)
def _annotated_fields(cls: type) -> dict[type, dict[str, Any]]:
    # note: The index structure is: {channel_type: {field_name: annotation}} resolved once per class.
    index: dict[type, dict[str, Any]] = {}
    hints = get_type_hints(cls, include_extras=True)
    for name, hint in hints.items():
        for annotation in getattr(hint, "__metadata__", ()):
            index.setdefault(type(annotation), {})[name] = annotation
    return index


# core: Warns about conflicting annotations between a class and a protocol.
@lru_cache(maxsize=None)
def _warn_if_protocol_shadows_annotations(cls: type, protocol: type, annotation: type) -> None:
    if _annotated_fields(cls).get(annotation):
        _logger.warning(
            "%s uses the %s protocol which has precedence over field annotations %s that are also used.",
            cls.__qualname__, protocol.__name__, annotation.__name__,
        )


def get_state_items(source: object, add: AddStateItem) -> None:
    annotations = _annotated_fields(type(source)).get(StateItem, {})
    if isinstance(source, WithStateItems):
        source.state_items(add)
        _warn_if_protocol_shadows_annotations(type(source), WithStateItems, StateItem)
    else:
        for name, annotation in annotations.items():
            state_item: StateItem = annotation
            add(name, getattr(source, name, state_item.default_value))


def get_state_items_all(source: object, add: AddStateItem) -> None:
    annotations = _annotated_fields(type(source)).get(StateItem, {})
    for name, annotation in annotations.items():
        state_item: StateItem = annotation
        if state_item.cascade:
            add(name, getattr(source, name, state_item.default_value))


def get_message_parts(source: object, append: AppendMessagePart) -> None:
    annotations = _annotated_fields(type(source)).get(MessagePart, {})
    if isinstance(source, WithMessageParts):
        source.message_parts(append)
        _warn_if_protocol_shadows_annotations(type(source), WithMessageParts, MessagePart)
    else:
        for name, annotation in annotations.items():
            message_part: MessagePart = annotation
            append(f"{message_part.label or name.capitalize()}: {getattr(source, name, None)}")


@dataclass(frozen=True)
class Caller:
    func: str
    file: str
    line: int


class LastCount:
    def __init__(self) -> None:
        self._value = 0

    def increment(self) -> None:
        self._value += 1

    @property
    def value(self) -> int:
        return self._value

    @property
    def overflows(self) -> bool:
        return self._value > 1

    @property
    def is_zero(self) -> bool:
        return self._value == 0


# meta: mirror of the C# delegates; structured-template + args, and key/value.
type AppendMessagePart = Callable[[str | None], None]
type AddStateItem = Callable[[str, Any], None]


@runtime_checkable
class WithStateItems(Protocol):
    # core: contributes structured fields to the log scope.
    def state_items(self, add: AddStateItem) -> None: ...


@runtime_checkable
class WithMessageParts(Protocol):
    # core: contributes human-readable parts to the rendered message.
    def message_parts(self, append: AppendMessagePart) -> None: ...


@runtime_checkable
class MessageSchema(Protocol):
    @abc.abstractmethod
    def compose(self, state_items: dict[str, Any], *sources: Any) -> str: ...


class _Forgiving(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"  # core: leave the hole visible rather than raise.


class CompactMessageSchema(MessageSchema):
    def __init__(self, separator: str = "; ") -> None:
        self._separator = separator

    def compose(self, state_items: dict[str, Any], *sources: Any) -> str:
        parts: list[str] = []

        def append(part: str | None) -> None:
            if part is not None:
                parts.append(part)

        for item in sources:
            get_message_parts(item, append)

        template = self._separator.join(part for part in parts)
        return template.format_map(_Forgiving(state_items))


class CompactMessagePrefix(WithMessageParts):
    def message_parts(self, append: AppendMessagePart) -> None:
        append("{activity[name]}[{activity[status]}]")
        append("Elapsed: {activity[elapsed_ms]} ms")


class WithCompactMessageSchema:
    message_schema: ClassVar[MessageSchema] = CompactMessageSchema()


@dataclass  # (frozen=True)
class Activity:
    tags: ClassVar[list[Any] | None] = None
    must_log_zero: ClassVar[bool] = False
    can_log_void: ClassVar[bool] = False

    @property
    def name(self) -> str:
        return type(self).__qualname__


@dataclass  # (frozen=True)
class Buzz(Activity):
    pass


@dataclass  # (frozen=True)
class Snap(Activity):
    pass


@dataclass  # (frozen=True)
class ActivityStatus[A: Activity]:
    # core: the phantom A binds a status to one activity type. It is consumed by
    # ActivityScope[A].log_status, which is what makes the type checker reject
    # logging activity X's status into a scope opened for activity Y.

    @property
    def code(self) -> str:
        # meta: Gets the status code from the concrete subclass but nearest to ActivityBuzz.
        for cls in type(self).__mro__:
            # note: Flags are derived directly from ActivityBuzz.
            if cls.__base__ is ActivityStatus:
                return cls.__name__
        raise TypeError(f"Activity status code not found because {type(self).__qualname__} does not inherit : must inherit from {ActivityStatus.__qualname__}.")


def resolve_status_level[A: Activity](activity: Activity, status: ActivityStatus[A]) -> int:
    match status:
        case Zero():
            if activity.must_log_zero:
                return logging.INFO
            else:
                return logging.DEBUG
        case Void():
            if activity.can_log_void:
                return logging.INFO
            else:
                return logging.DEBUG
        case Noop():
            return logging.DEBUG
        case Okay():
            return logging.INFO
        case Fail():
            # if logged_on_exit := type(status) is Fail:
            #    return logging.DEBUG
            # else:
            #    return logging.ERROR
            return logging.ERROR
        case _:
            return logging.INFO


# core: everything went according to plan.
@dataclass  # (frozen=True)
class Okay[A: Activity](ActivityStatus[A]):
    pass


# core: an error occurred.
@dataclass  # (frozen=True)
class Fail[A: Activity](ActivityStatus[A]):
    exception: Exception | None

    def message_parts(self, append: AppendMessagePart) -> None:
        if self.exception is not None:
            append(f"Exception: {str(self.exception)}")


# note: the very first status. Its previous name was "First".
@dataclass  # (frozen=True)
class Zero[A: Activity](ActivityStatus[A]):
    pass


@dataclass  # (frozen=True)
class Void[A: Activity](ActivityStatus[A]):
    reason: Annotated[str, StateItem(), MessagePart()]


@dataclass  # (frozen=True)
class Noop[A: Activity](ActivityStatus[A]):
    pass


class BuzzCounter:
    """Internal accumulator used when a buzz counts repeated work."""

    def __init__(self) -> None:
        self.item_count = 0
        self._status_counts: dict[str, int] = {}
        self.duration_ms = 0
        self.duration_ms_min: int | None = None
        self.duration_ms_max: int | None = None
        self._duration_ms_mean = 0.0
        self._duration_ms_m2 = 0.0

    def count(self, status: ActivityStatus[Any], duration_ms: int) -> None:
        # core: Each buzz item contributes exactly one outcome to the parent buzz summary.
        self.item_count += 1
        code = status.code.lower()
        self._status_counts[code] = self._status_counts.get(code, 0) + 1
        self.duration_ms += duration_ms
        self.duration_ms_min = duration_ms if self.duration_ms_min is None else min(self.duration_ms_min, duration_ms)
        self.duration_ms_max = duration_ms if self.duration_ms_max is None else max(self.duration_ms_max, duration_ms)

        # util: Welford's algorithm tracks variance without storing each item duration.
        delta = duration_ms - self._duration_ms_mean
        self._duration_ms_mean += delta / self.item_count
        delta2 = duration_ms - self._duration_ms_mean
        self._duration_ms_m2 += delta * delta2

    def __bool__(self) -> bool:
        # core: A counter only contributes telemetry after at least one buzz item was completed.
        return self.item_count > 0

    @property
    def duration_ms_mean(self) -> float:
        return self._duration_ms_mean

    @property
    def duration_ms_std_dev(self) -> float:
        return (self._duration_ms_m2 / (self.item_count - 1)) ** 0.5 if self.item_count > 1 else 0.0

    @property
    def throughput_s(self) -> float:
        return self.item_count / (self.duration_ms / 1000) if self.duration_ms else 0.0

    def rate_of(self, code: str) -> float:
        return self._status_counts[code] / self.item_count if self.item_count else 0.0

    def state_items(self, add: AddStateItem) -> None:
        if not self:
            return
        add("item_count", self.item_count)
        for code, count in self._status_counts.items():
            add(f"{code}_count", count)
            add(f"{code}_rate", self.rate_of(code))
        add("duration_ms", self.duration_ms)
        add("duration_ms_mean", self.duration_ms_mean)
        add("duration_ms_min", self.duration_ms_min)
        add("duration_ms_max", self.duration_ms_max)
        add("duration_ms_std_dev", self.duration_ms_std_dev)
        add("throughput_s", self.throughput_s)

    def message_parts(self, append: AppendMessagePart) -> None:
        if not self:
            return
        for code in self._status_counts:
            append(f"{code.capitalize()}: {{state[{code}_rate]:0.1%}} ({{state[{code}_count]}} of {{state[item_count]}})")
        append("Throughput: {state[throughput_s]:0.1f}/s")


class ActivityScope[A: Activity]:
    _stack: ClassVar[ContextVar[ActivityScope[Any] | None]] = ContextVar("current_activity", default=None)
    message_schema: ClassVar[MessageSchema] = CompactMessageSchema()
    message_prefix: ClassVar[WithMessageParts] = CompactMessagePrefix()

    def __init__(self, activity: A, trace_id: Any | None, caller: Caller | None = None) -> None:
        self._activity = activity
        self.trace_id: str = trace_id or secrets.token_hex(16)
        self.scope_id: str = secrets.token_hex(8)  # note: python reserves id already.
        self.parent: ActivityScope[Any] | None = None  # core: This is going to be set on __enter__.
        self.caller = caller
        self.stopwatch: Stopwatch = Stopwatch()
        self._last_count = LastCount()
        self._logger: logging.Logger = logging.getLogger(activity.name)
        self._buzz_counter = BuzzCounter()

    def __iter__(self) -> Iterator[ActivityScope[Any]]:
        current: ActivityScope[Any] | None = self
        while current:
            yield current
            current = current.parent

    @property
    def depth(self) -> int:
        return self.parent.depth + 1 if self.parent else 0

    def to_extra(self, status: str | None, state: dict[str, Any] | None) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.scope_id,
            "parent_id": self.parent.scope_id if self.parent else None,
            "activity": {
                "name": self._activity.name,
                "path": PathOf(reversed(list(self)), lambda a: a._activity.name),
                "depth": self.depth,
                "status": status.lower() if status else None,
                "elapsed_ms": self.stopwatch.elapsed_ms,
                "logs_from": {
                    "func": self.caller.func,
                    "file": self.caller.file,
                    "line": self.caller.line,
                } if self.caller else None,
                "tags": self._activity.tags
            },
            "state": state
        }

    def log_status(self, status: ActivityStatus[A]) -> ActivityScope[A]:
        self._last_count.increment()
        return self._log(status)

    def _log(self, status: ActivityStatus[A]) -> ActivityScope[A]:

        state: dict[str, Any] = {}

        def set_state_item(key: str, value: Any) -> None:
            if value is not None:
                state[key] = value

        # core: Get cascading state items from the parent scopes.
        # note: Collect state items from top to bottom so that the last status wins.
        for item in reversed(list(islice(iter(self), 1, None))):
            get_state_items_all(item._activity, set_state_item)

        # core: Activity, buzz counter, and status each get a chance to fulfill the monitoring contract.
        sources: list[object] = [self._activity, self._buzz_counter, status]

        for item in sources:
            get_state_items(item, set_state_item)

        extra: dict[str, Any] = self.to_extra(status.code, state)

        message = self.message_schema.compose(extra, self.message_prefix, *sources)
        status_level = resolve_status_level(self._activity, status)

        # core: Special overflow handling for the last status.
        if self._last_count.overflows:
            status_level = logging.DEBUG
            _logger.warning(f"Last status logged {self._last_count.value} times. This is a bug.")

        self._logger.log(status_level, message, extra={"wiretap": extra})
        return self

    @classmethod
    def current(cls) -> ActivityScope[Any] | None:
        return cls._stack.get()

    @contextmanager
    def push(self) -> Iterator[None]:
        # meta: ContextVar stack mechanics are shared by all concrete scope lifecycles.
        if parent := ActivityScope._stack.get():
            self.parent = parent
            # core: Parent's trace ID needs to be propagated to child scopes.
            self.trace_id = parent.trace_id

        token = ActivityScope._stack.set(self)
        try:
            yield
        finally:
            ActivityScope._stack.reset(token)
            self.parent = None


class BuzzScope[A: Buzz](ActivityScope[A]):
    def begin_item[B: Activity](self, activity: B, frame_offset: int = 0) -> "BuzzItemScope[B]":
        # core: Begins one item inside this buzz summary.
        return BuzzItemScope(activity, self._buzz_counter, self.trace_id, _create_caller(frame_offset + 1, True))

    def __enter__(self) -> "BuzzScope[A]":
        self._scope = self.push()
        self._scope.__enter__()
        self._log(Zero())
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if self._last_count.is_zero:
                if exc_type is not None:
                    self._log(Fail(exception=exc))
                else:
                    self._log(Void(reason="Last status not specified and automatically logged."))
        finally:
            self._scope.__exit__(exc_type, exc, tb)


class SnapScope[A: Snap](ActivityScope[A]):
    def __enter__(self) -> "SnapScope[A]":
        self._scope = self.push()
        self._scope.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._scope.__exit__(exc_type, exc, tb)


class BuzzItemStatus[A: Activity]:
    def __init__(self, log: Callable[[], None]) -> None:
        self._log = log

    def log(self) -> None:
        self._log()


class BuzzItemScope[A: Activity](ActivityScope[A]):
    def __init__(self, activity: A, counter: BuzzCounter, trace_id: Any | None, caller: Caller | None = None) -> None:
        super().__init__(activity, trace_id, caller)
        self._counter = counter
        self._status: ActivityStatus[A] | None = None

    def set_status(self, status: ActivityStatus[A]) -> BuzzItemStatus[A]:
        self._status = status

        # util: Adapts log_status, which returns the scope, into a terminal status action.
        def log() -> None:
            self.log_status(status)

        return BuzzItemStatus(log)

    def log_status(self, status: ActivityStatus[A]) -> "BuzzItemScope[A]":
        super().log_status(status)
        return self

    def __enter__(self) -> "BuzzItemScope[A]":
        self._scope = self.push()
        self._scope.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            # core: A buzz item without an explicit status is intentionally inconclusive.
            self._counter.count(self._status or Noop(), self.stopwatch.elapsed_ms)
        finally:
            self._scope.__exit__(exc_type, exc, tb)


FRAME_INDEX_CALLER = 1


def _create_caller(frame_offset: int, with_caller_info: bool) -> Caller | None:
    if with_caller_info:
        frame = inspect.currentframe()
        try:
            steps = FRAME_INDEX_CALLER + frame_offset
            for _ in range(steps):
                if frame is None:
                    break
                frame = frame.f_back

            caller = Caller(
                func=frame.f_code.co_name if frame is not None else "<unknown>",
                file=trim_path(frame.f_code.co_filename) if frame is not None else "<unknown>",
                line=frame.f_lineno if frame is not None else 0
            )
        finally:
            del frame
    else:
        return None

    return caller


def begin_buzz[A: Buzz](activity: A, trace_id: Any | None = None, frame_offset: int = 0, with_caller_info: bool = True) -> BuzzScope[A]:
    if not isinstance(activity, Buzz):
        raise TypeError(f"{type(activity).__qualname__} cannot begin because it is not a Buzz activity.")
    caller = _create_caller(frame_offset, with_caller_info)
    return BuzzScope(activity, trace_id, caller)


def begin_snap[A: Snap](activity: A, trace_id: Any | None = None, frame_offset: int = 0) -> SnapScope[A]:
    return SnapScope(activity, trace_id, _create_caller(frame_offset, True))


@dataclass
class PrototypeBuzz(Buzz):
    """
    A prototype buzz activity for testing and development purposes.
    """
    tags = ["prototype-buzz"]

    def __init__(self, name: str, message: str | None = None, **kwargs) -> None:
        self._name = name
        self._message = message
        self._state = kwargs

    @property
    def name(self) -> str:
        return self._name

    def state_items(self, add: AddStateItem) -> None:
        for key, value in self._state.items():
            add(key, value)

    def message_parts(self, append: AppendMessagePart) -> None:
        append(self._message)

    @dataclass
    class Void(Void["PrototypeBuzz"]):
        def __init__(self, message: str | None = None, **kwargs) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, add: AddStateItem) -> None:
            for key, value in self._state.items():
                add(key, value)

        def message_parts(self, append: AppendMessagePart) -> None:
            append(self._message)

    @dataclass
    class Okay(Okay["PrototypeBuzz"]):
        def __init__(self, message: str | None = None, **kwargs) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, add: AddStateItem) -> None:
            for key, value in self._state.items():
                add(key, value)

        def message_parts(self, append: AppendMessagePart) -> None:
            append(self._message)

    @dataclass
    class Fail(Fail["PrototypeBuzz"]):
        def __init__(self, message: str | None = None, **kwargs) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, add: AddStateItem) -> None:
            for key, value in self._state.items():
                add(key, value)

        def message_parts(self, append: AppendMessagePart) -> None:
            append(self._message)


@dataclass
class PrototypeSnap(Snap):
    """
    A prototype snap activity for testing and development purposes.
    """
    tags = ["prototype-snap"]

    def __init__(self, name: str, message: str | None = None, **kwargs) -> None:
        self._name = name
        self._message = message
        self._state = kwargs

    @property
    def name(self) -> str:
        return self._name

    def state_items(self, add: AddStateItem) -> None:
        for key, value in self._state.items():
            add(key, value)

    def message_parts(self, append: AppendMessagePart) -> None:
        append(self._message)

    @dataclass
    class Okay(Okay["PrototypeSnap"]):
        def __init__(self, message: str | None = None, **kwargs) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, add: AddStateItem) -> None:
            for key, value in self._state.items():
                add(key, value)

        def message_parts(self, append: AppendMessagePart) -> None:
            append(self._message)


def log_status[A: Snap](snap: A, flag: ActivityStatus[A]) -> None:
    with begin_snap(snap, frame_offset=2) as scope:
        scope.log_status(flag)
