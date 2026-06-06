from __future__ import annotations

import abc
import inspect
import logging
import secrets
from contextlib import contextmanager
from contextvars import ContextVar  # noqa: built-in module
from dataclasses import dataclass, field
from functools import lru_cache, cache
from itertools import islice
from typing import Any, Iterator, ClassVar, runtime_checkable, Protocol, Callable, Annotated, get_type_hints

from wiretap.meta import trim_path
from wiretap.util.path_of import PathOf
from wiretap.util.stopwatch import Stopwatch

# util: Internal logger.
_logger = logging.getLogger("wiretap")


@dataclass(frozen=True)
class FeedToStateItem:
    # core: When True, the value cascades to all activities down the stack.
    cascade: bool = field(default=False)
    default_value: Any = field(default=None)


@dataclass(frozen=True)
class FeedToMessagePart:
    label: str | None = None


# core: Reads and caches annotated fields for status classes because they use [Annotated] fields.
@cache
def _annotated_fields(cls: type) -> dict[type, dict[str, Any]]:
    # note: The index structure is: {channel_type: {field_name: annotation}} resolved once per class.
    index: dict[type, dict[str, Any]] = {}
    hints = get_type_hints(cls, include_extras=True)
    for name, hint in hints.items():
        for annotation in getattr(hint, "__metadata__", ()):
            index.setdefault(type(annotation), {})[name] = annotation
    return index


# core: Warns about conflicting annotations between a class and a protocol.
@cache
def _warn_if_protocol_shadows_annotations(cls: type, protocol: type, annotation: type) -> None:
    if _annotated_fields(cls).get(annotation):
        _logger.warning(
            "%s uses the %s protocol which has precedence over field annotations %s that are also used.",
            cls.__qualname__, protocol.__name__, annotation.__name__,
        )


def get_state_items(source: object, push_state_item: PushStateItem) -> None:
    annotations = _annotated_fields(type(source)).get(FeedToStateItem, {})  # type: ignore[arg-type]
    if isinstance(source, StateItemFeed):
        source.state_items(push_state_item)
        _warn_if_protocol_shadows_annotations(type(source), StateItemFeed, FeedToStateItem)
    else:
        for name, annotation in annotations.items():
            state_item: FeedToStateItem = annotation
            push_state_item(name, getattr(source, name, state_item.default_value))


def get_state_items_cascading(source: object, push: PushStateItem) -> None:
    annotations = _annotated_fields(type(source)).get(FeedToStateItem, {})  # type: ignore[arg-type]
    for name, annotation in annotations.items():
        state_item: FeedToStateItem = annotation
        if state_item.cascade:
            push(name, getattr(source, name, state_item.default_value))


def get_message_parts(source: object, push: PushMessagePart) -> None:
    annotations = _annotated_fields(type(source)).get(FeedToMessagePart, {})  # type: ignore[arg-type]
    if isinstance(source, MessagePartFeed):
        source.message_parts(push)
        _warn_if_protocol_shadows_annotations(type(source), MessagePartFeed, FeedToMessagePart)
    else:
        for name, annotation in annotations.items():
            message_part: FeedToMessagePart = annotation
            push(f"{message_part.label or name.capitalize()}: {getattr(source, name, None)}")


FRAME_INDEX_CALLER = 1


@dataclass(frozen=True)
class Caller:
    func: str
    file: str
    line: int

    @staticmethod
    def from_current_frame(frame_offset: int) -> "Caller":
        # meta: Uses Python frame inspection to capture where the public API was called.
        frame = inspect.currentframe()
        try:
            steps = FRAME_INDEX_CALLER + frame_offset
            for _ in range(steps):
                if frame is None:
                    break
                frame = frame.f_back

            return Caller(
                func=frame.f_code.co_name if frame is not None else "<unknown>",
                file=trim_path(frame.f_code.co_filename) if frame is not None else "<unknown>",
                line=frame.f_lineno if frame is not None else 0
            )
        finally:
            del frame


class LastStatusCount:
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


type PushMessagePart = Callable[[str | None], None]
type PushStateItem = Callable[[str, Any], None]


@runtime_checkable
class StateItemFeed(Protocol):
    # core: Feeds structured fields to the log scope.
    def state_items(self, push: PushStateItem) -> None: ...


@runtime_checkable
class MessagePartFeed(Protocol):
    # core: Feeds human-readable parts to the rendered message.
    def message_parts(self, push: PushMessagePart) -> None: ...


@runtime_checkable
class ComposeMessage(Protocol):
    @abc.abstractmethod
    def __call__(self, state_items: dict[str, Any], *sources: Any) -> str: ...


class _Forgiving(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"  # core: leave the hole visible rather than raise.


class MessageHeaderFeed(MessagePartFeed):
    def message_parts(self, push: PushMessagePart) -> None:
        push("{activity[name]}[{activity[status]}]")
        push("Elapsed: {activity[elapsed_ms]} ms")


class ComposeMessageByAppending(ComposeMessage):
    def __init__(self, header: MessagePartFeed = MessageHeaderFeed(), separator: str = "; ") -> None:
        self._header = header
        self._separator = separator

    def __call__(self, state_items: dict[str, Any], *sources: Any) -> str:
        parts: list[str] = []

        def append(part: str | None) -> None:
            if part is not None:
                parts.append(part)

        get_message_parts(self._header, append)
        for item in sources:
            get_message_parts(item, append)

        template = self._separator.join(part for part in parts)
        return template.format_map(_Forgiving(state_items))


@dataclass  # (frozen=True)
class Activity:
    tags: ClassVar[list[Any] | None] = None

    @property
    def name(self) -> str:
        return type(self).__qualname__


@dataclass  # (frozen=True)
class Buzz(Activity):
    must_log_zero: ClassVar[bool] = False
    can_log_void: ClassVar[bool] = False


@dataclass  # (frozen=True)
class Snap(Activity):
    pass


@dataclass  # (frozen=True)
class ActivityStatus[A: Activity]:
    # core: the phantom A binds a status to one activity type. It is consumed by
    # ActivityScope[A].log_status, which is what makes the type checker reject
    # logging activity X's status into a scope opened for activity Y.
    level: ClassVar[int] = logging.INFO

    @property
    def code(self) -> str:
        # meta: Gets the status code from the concrete subclass but nearest to ActivityBuzz.
        for cls in type(self).__mro__:
            # note: Flags are derived directly from ActivityBuzz.
            if cls.__base__ is ActivityStatus:
                return cls.__name__
        raise TypeError(f"Activity status code not found because {type(self).__qualname__} does not inherit : must inherit from {ActivityStatus.__qualname__}.")


# core: everything went according to plan.
@dataclass  # (frozen=True)
class Okay[A: Activity](ActivityStatus[A]):
    level: ClassVar[int] = logging.INFO


# core: an error occurred.
@dataclass  # (frozen=True)
class Fail[A: Activity](ActivityStatus[A]):
    level: ClassVar[int] = logging.ERROR
    exception: Exception | None

    def message_parts(self, push: PushMessagePart) -> None:
        if self.exception is not None:
            push(f"Exception: {str(self.exception)}")


# note: the very first status. Its previous name was "First".
@dataclass  # (frozen=True)
class Zero[A: Activity](ActivityStatus[A]):
    level: ClassVar[int] = logging.DEBUG


@dataclass  # (frozen=True)
class Void[A: Activity](ActivityStatus[A]):
    level: ClassVar[int] = logging.DEBUG
    reason: Annotated[str, FeedToStateItem(), FeedToMessagePart()]


@dataclass  # (frozen=True)
class Noop[A: Activity](ActivityStatus[A]):
    level: ClassVar[int] = logging.DEBUG


class BuzzBatch:
    """Internal accumulator used when a buzz processes repeated items."""

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
        # core: A batch only contributes telemetry after at least one buzz item was completed.
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

    def state_items(self, push: PushStateItem) -> None:
        if not self:
            return
        push("item_count", self.item_count)
        for code, count in self._status_counts.items():
            push(f"{code}_count", count)
            push(f"{code}_rate", self.rate_of(code))
        push("duration_ms", self.duration_ms)
        push("duration_ms_mean", self.duration_ms_mean)
        push("duration_ms_min", self.duration_ms_min)
        push("duration_ms_max", self.duration_ms_max)
        push("duration_ms_std_dev", self.duration_ms_std_dev)
        push("throughput_s", self.throughput_s)

    def message_parts(self, push: PushMessagePart) -> None:
        if not self:
            return
        for code in self._status_counts:
            push(f"{code.capitalize()}: {{state[{code}_rate]:0.1%}} ({{state[{code}_count]}} of {{state[item_count]}})")
        push("Throughput: {state[throughput_s]:0.1f}/s")


class ActivityScope[A: Activity]:
    _stack: ClassVar[ContextVar[ActivityScope[Any] | None]] = ContextVar("current_activity", default=None)
    compose_message: ClassVar[ComposeMessage] = ComposeMessageByAppending()

    def __init__(self, activity: A, trace_id: Any | None, caller: Caller | None = None) -> None:
        self._activity = activity
        self.trace_id: str = trace_id or secrets.token_hex(16)
        self.scope_id: str = secrets.token_hex(8)  # note: python reserves id already.
        self.parent: ActivityScope[Any] | None = None  # core: This is going to be set on __enter__.
        self.caller = caller
        self.stopwatch: Stopwatch = Stopwatch()
        self._last_status = LastStatusCount()
        self._buzz_batch = BuzzBatch()
        self._logger: logging.Logger = logging.getLogger(activity.name)

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
        self._last_status.increment()
        return self._log(status)

    def _log(self, status: ActivityStatus[A]) -> ActivityScope[A]:

        state: dict[str, Any] = {}

        def set_state_item(key: str, value: Any) -> None:
            if value is not None:
                state[key] = value

        # core: Get cascading state items from the parent scopes.
        # note: Collect state items from top to bottom so that the last status wins.
        for item in reversed(list(islice(iter(self), 1, None))):
            get_state_items_cascading(item._activity, set_state_item)

        # core: Activity, buzz batch, and status each get a chance to fulfill the monitoring contract.
        sources: list[Any] = [self._activity, self._buzz_batch, status]

        for item in sources:
            get_state_items(item, set_state_item)

        extra: dict[str, Any] = self.to_extra(status.code, state)

        message = self.compose_message(extra, *sources)
        status_level = self.get_status_level_or_default(status)

        # core: Special overflow handling for the last status.
        if self._last_status.overflows:
            status_level = logging.DEBUG
            _logger.warning(f"Last status logged {self._last_status.value} times. This is a bug.")

        self._logger.log(status_level, message, extra={"wiretap": extra})
        return self

    def get_status_level_or_default(self, status: ActivityStatus[A]) -> int:
        # util: Concrete scopes can adjust lifecycle statuses without a global resolver.
        return status.level

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
    def get_status_level_or_default(self, status: ActivityStatus[A]) -> int:
        # core: Buzz lifecycle flags can promote automatic lifecycle statuses to core logs.
        match status:
            case Zero():
                if self._activity.must_log_zero:
                    return logging.INFO
            case Void():
                if self._activity.can_log_void:
                    return logging.INFO

        return super().get_status_level_or_default(status)

    def begin_item[B: Activity](self, activity: B, frame_offset: int = 0) -> "BuzzItemScope[B]":
        # core: Begins one item inside this buzz summary.
        return BuzzItemScope(activity, self._buzz_batch, self.trace_id, Caller.from_current_frame(frame_offset + 1))

    def __enter__(self) -> "BuzzScope[A]":
        self._scope = self.push()
        self._scope.__enter__()
        self._log(Zero())
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if self._last_status.is_zero:
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
    def __init__(self, activity: A, batch: BuzzBatch, trace_id: Any | None, caller: Caller | None = None) -> None:
        super().__init__(activity, trace_id, caller)
        self._batch = batch
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
            self._batch.count(self._status or Noop(), self.stopwatch.elapsed_ms)
        finally:
            self._scope.__exit__(exc_type, exc, tb)


def begin_buzz[A: Buzz](activity: A, trace_id: Any | None = None, frame_offset: int = 0, with_caller_info: bool = True) -> BuzzScope[A]:
    if not isinstance(activity, Buzz):
        raise TypeError(f"{type(activity).__qualname__} cannot begin because it is not a Buzz activity.")
    caller = Caller.from_current_frame(frame_offset) if with_caller_info else None
    return BuzzScope(activity, trace_id, caller)


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

    def state_items(self, push: PushStateItem) -> None:
        for key, value in self._state.items():
            push(key, value)

    def message_parts(self, push: PushMessagePart) -> None:
        push(self._message)

    @dataclass
    class Void(Void["PrototypeBuzz"]):
        def __init__(self, message: str | None = None, **kwargs) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, push: PushStateItem) -> None:
            for key, value in self._state.items():
                push(key, value)

        def message_parts(self, push: PushMessagePart) -> None:
            push(self._message)

    @dataclass
    class Okay(Okay["PrototypeBuzz"]):
        def __init__(self, message: str | None = None, **kwargs) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, push: PushStateItem) -> None:
            for key, value in self._state.items():
                push(key, value)

        def message_parts(self, push: PushMessagePart) -> None:
            push(self._message)

    @dataclass
    class Fail(Fail["PrototypeBuzz"]):
        def __init__(self, message: str | None = None, **kwargs) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, push: PushStateItem) -> None:
            for key, value in self._state.items():
                push(key, value)

        def message_parts(self, push: PushMessagePart) -> None:
            push(self._message)


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

    def state_items(self, push: PushStateItem) -> None:
        for key, value in self._state.items():
            push(key, value)

    def message_parts(self, push: PushMessagePart) -> None:
        push(self._message)

    @dataclass
    class Okay(Okay["PrototypeSnap"]):
        def __init__(self, message: str | None = None, **kwargs) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, push: PushStateItem) -> None:
            for key, value in self._state.items():
                push(key, value)

        def message_parts(self, push: PushMessagePart) -> None:
            push(self._message)


def log_status[A: Snap](snap: A, flag: ActivityStatus[A], trace_id: Any | None = None) -> None:
    with SnapScope(snap, trace_id, Caller.from_current_frame(2)) as scope:
        scope.log_status(flag)
