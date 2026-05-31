import abc
import contextlib
import inspect
import logging
import secrets
import sys
from abc import ABC
from contextvars import ContextVar  # noqa: built-in module
from dataclasses import dataclass, fields, is_dataclass, field
from enum import Enum
from functools import reduce, cache, lru_cache
from inspect import FrameInfo
from types import FrameType
from typing import Optional, Any, Iterator, TypeVar, ClassVar, Literal, runtime_checkable, Protocol, Callable, Self, \
    Annotated, get_type_hints

from wiretap.util.stopwatch import Stopwatch

_logger = logging.getLogger("wiretap")


@dataclass(frozen=True)
class StateItem:
    default_value: Any = field(default=None)


@dataclass(frozen=True)
class MessagePart:
    label: str | None = None


@lru_cache(maxsize=None)
def _annotated_fields(cls: type) -> dict[type, dict[str, Any]]:
    # note: The index structure is: {channel_type: {field_name: annotation}} resolved once per class.
    index: dict[type, dict[str, Any]] = {}
    hints = get_type_hints(cls, include_extras=True)
    for name, hint in hints.items():
        for annotation in getattr(hint, "__metadata__", ()):
            index.setdefault(type(annotation), {})[name] = annotation
    return index


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

    def to_dict(self) -> dict:
        return {"last_index": self._value}

    @property
    def is_zero(self) -> bool:
        return self._value == 0


# meta: mirror of the C# delegates; structured-template + args, and key/value.
type AppendMessagePart = Callable[[str], None]
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


@dataclass(frozen=True)
class Activity(ABC):
    tags: ClassVar[dict[str, Any] | None] = None
    must_log_zero: ClassVar[bool] = False
    can_log_void: ClassVar[bool] = False

    @property
    def name(self) -> str:
        return type(self).__qualname__


@dataclass(frozen=True)
class ActivityBuzz[A: Activity]:
    # core: the phantom A binds a status to one activity type. It is consumed by
    # ActivityScope[A].log_status, which is what makes the type checker reject
    # logging activity X's status into a scope opened for activity Y.

    @property
    def code(self) -> str:
        # meta: Gets the status code from the concrete subclass but nearest to ActivityBuzz.
        for cls in type(self).__mro__:
            # note: Flags are derived directly from ActivityBuzz.
            if cls.__base__ is ActivityBuzz:
                return cls.__name__
        raise TypeError(f"Activity status code not found because {type(self).__qualname__} does not inherit : must inherit from {ActivityBuzz.__qualname__}.")


def resolve_buzz_level[A: Activity](activity: Activity, buzz: ActivityBuzz[A]) -> int:
    match buzz:
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
        case Okay():
            return logging.INFO
        case Fail():
            if auto := type(buzz) is Fail:
                return logging.DEBUG
            else:
                return logging.ERROR
        case _:
            return logging.INFO


# core: everything went according to plan.
@dataclass(frozen=True)
class Okay[A: Activity](ActivityBuzz[A]):
    pass


@dataclass(frozen=True)
class Flag[A: Activity](ActivityBuzz[A], Activity):
    pass


# core: an error occurred.
@dataclass(frozen=True)
class Fail[A: Activity](ActivityBuzz[A]):
    exception: Exception | None

    def message_parts(self, append: AppendMessagePart) -> None:
        if self.exception is not None:
            append(f"Exception: {str(self.exception)}")


# note: the very first status. Its previous name was "First".
@dataclass(frozen=True)
class Zero[A: Activity](ActivityBuzz[A]):
    pass


# core: emitted while the activity runs; carries an ad-hoc message. The level is a
# constructor argument now — debug/trace are factory methods, not subclasses.
@dataclass(frozen=True)
class Note[A: Activity](ActivityBuzz[A], Activity):
    message: Annotated[str, MessagePart()]


@dataclass(frozen=True)
class Void[A: Activity](ActivityBuzz[A]):
    reason: Annotated[str, StateItem(), MessagePart()]


def is_last(status: ActivityBuzz[Any]) -> bool:
    match status:
        case Flag() | Void() | Okay() | Fail():
            return True
        case _:
            return False


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
                "depth": self.depth,
                "status": status.lower() if status else None,
                "elapsed_ms": self.stopwatch.elapsed_ms,
                "tags": self._activity.tags
            },
            "state": state,
            "source": {
                "func": self.caller.func,
                "file": self.caller.file,
                "line": self.caller.line,
            } if self.caller else None,
        }

    @classmethod
    def begin(cls, activity: A, trace_id: Any | None, caller: Caller | None) -> ActivityScope[A]:
        return cls(activity, trace_id, caller)

    def log_buzz(self, buzz: Void[A] | Okay[A] | Fail[A]) -> ActivityScope[A]:
        if isinstance(buzz, Flag):
            # note: Flags are also activities so create a new scope for them.
            with begin_scope(buzz, frame_offset=1) as scope:
                return scope._log(buzz)
        else:
            return self._log(buzz)

    def _log(self, status: ActivityBuzz[A]) -> ActivityScope[A]:

        state: dict[str, Any] = {}

        def set_state_item(key: str, value: Any) -> None:
            if value is not None:
                state[key] = value

        for item in [self._activity, status]:
            get_state_items(item, set_state_item)

        extra: dict[str, Any] = self.to_extra(status.code, state)

        if is_last(status):
            self._last_count.increment()

        # note: Some buzzes like Flag implement both the status and the activity, so it is the same object.
        sources = dict.fromkeys([self._activity, status]) # meta: ordered and deduped
        message = self.message_schema.compose(extra, self.message_prefix, *sources)
        status_level = resolve_buzz_level(self._activity, status)

        # core: Special overflow handling for the last status.
        if self._last_count.overflows:
            status_level = logging.DEBUG
            extra |= self._last_count.to_dict()

        self._logger.log(status_level, message, extra={"wiretap": extra})
        return self

    @classmethod
    def current(cls) -> ActivityScope[Any] | None:
        return cls._stack.get()

    def __enter__(self) -> ActivityScope[A]:
        if parent := ActivityScope._stack.get():
            self.parent = parent

        self._token = ActivityScope._stack.set(self)

        match self._activity:
            case Flag() | Note():
                # note: Flags and Notes do not have the zero status.
                pass
            case _:
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
            ActivityScope._stack.reset(self._token)
            self.parent = None


FRAME_INDEX_SELF = 0
FRAME_INDEX_CALLER = 1


def begin_scope[A: Activity](activity: A, trace_id: Any | None = None, frame_offset: int = 0) -> ActivityScope[A]:
    frame = sys._getframe(FRAME_INDEX_CALLER + frame_offset)
    caller = Caller(
        func=frame.f_code.co_name,
        file=frame.f_code.co_filename,
        line=frame.f_lineno,
    )
    return ActivityScope.begin(activity, trace_id, caller)


@dataclass(frozen=True)
class Prototyping(Activity):
    must_log_zero = True
    activity_name: str
    state: dict[str, Any] | None

    @dataclass(frozen=True)
    class Note(Note):
        message: str

    @dataclass(frozen=True)
    class Okay(Okay):
        message: str

    @dataclass(frozen=True)
    class Fail(Fail):
        message: str


def log_note(message: str) -> None:
    if scope := ActivityScope.current():
        scope._log(Note(message=message))


def log_flag(buzz: Flag) -> None:
    # note: Flags are also activities so create a new scope for them.
    with begin_scope(buzz, frame_offset=1) as scope:
        return scope._log(buzz)
