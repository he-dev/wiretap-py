from __future__ import annotations

import abc
import inspect
import logging
import secrets
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

    def log_status(self, status: Void[A] | Okay[A] | Fail[A]) -> ActivityScope[A]:
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

        # core: Activity, scope, and status each get a chance to fulfill the monitoring contract.
        for item in [self._activity, self, status]:
            get_state_items(item, set_state_item)

        extra: dict[str, Any] = self.to_extra(status.code, state)

        message = self.message_schema.compose(extra, self.message_prefix, self._activity, self, status)
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

    def __enter__(self) -> ActivityScope[A]:
        if parent := ActivityScope._stack.get():
            self.parent = parent
            # core: Parent's trace ID needs to be propagated to child scopes.
            self.trace_id = parent.trace_id

        self._token = ActivityScope._stack.set(self)

        match self._activity:
            case Snap():
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


@runtime_checkable
class ActivityScopeFactory[A: Activity](Protocol):
    # core: Allows an activity contract to choose its runtime scope implementation.
    def create_scope(self, trace_id: Any | None, caller: Caller | None) -> ActivityScope[A]: ...


def begin_buzz[A: Activity](activity: A, trace_id: Any | None = None, frame_offset: int = 0, with_caller_info: bool = True) -> ActivityScope[A]:
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
        caller = None

    if isinstance(activity, ActivityScopeFactory):
        return activity.create_scope(trace_id, caller)

    return ActivityScope(activity, trace_id, caller)


def begin_snap[A: Snap](activity: A, trace_id: Any | None = None, frame_offset: int = 0) -> ActivityScope[A]:
    return begin_buzz(activity, trace_id, frame_offset)


@dataclass
class Prototype(Activity):
    """
    A prototype activity for testing and development purposes.
    """
    tags = ["prototype"]

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
    class Void(Void):
        def __init__(self, message: str | None = None, **kwargs) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, add: AddStateItem) -> None:
            for key, value in self._state.items():
                add(key, value)

        def message_parts(self, append: AppendMessagePart) -> None:
            append(self._message)

    @dataclass
    class Okay(Okay):
        def __init__(self, message: str | None = None, **kwargs) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, add: AddStateItem) -> None:
            for key, value in self._state.items():
                add(key, value)

        def message_parts(self, append: AppendMessagePart) -> None:
            append(self._message)

    @dataclass
    class Fail(Fail):
        def __init__(self, message: str | None = None, **kwargs) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, add: AddStateItem) -> None:
            for key, value in self._state.items():
                add(key, value)

        def message_parts(self, append: AppendMessagePart) -> None:
            append(self._message)


def log_status[A: Snap](snap: Snap, flag: Okay[A]) -> None:
    with begin_snap(snap, frame_offset=2) as snap:
        snap.log_status(flag)
