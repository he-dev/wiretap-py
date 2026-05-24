import abc
import contextlib
import inspect
import logging
import secrets
from abc import ABC
from contextvars import ContextVar  # noqa: built-in module
from dataclasses import dataclass, fields, is_dataclass, field
from enum import Enum
from functools import reduce, cache
from inspect import FrameInfo
from typing import Optional, Any, Iterator, TypeVar, ClassVar, Literal, runtime_checkable, Protocol, Callable, Self, \
    Annotated, get_type_hints

from wiretap.util.stopwatch import Stopwatch

# meta: stdlib logging has no TRACE; the role model's lowest level needs one.
TRACE = 5
logging.addLevelName(TRACE, "TRACE")


class LastIndex:
    def __init__(self) -> None:
        self._value = -1

    def increment(self) -> None:
        self._value += 1

    @property
    def value(self) -> int:
        return self._value

    @property
    def overflows(self) -> bool:
        return self._value > 0

    def to_dict(self) -> dict:
        return {"last_index": self._value}

    def __bool__(self) -> bool:
        return self._value >= 0


def state_item(**kwargs):
    return field(metadata={"state_item": True}, **kwargs)


# meta: mirror of the C# delegates; structured-template + args, and key/value.
type AppendMessagePart = Callable[[str], None]
type SetStateItem = Callable[[str, Any], None]


# @runtime_checkable
class WithStateItems(ABC):
    # core: contributes structured fields to the log scope.
    def state_items(self, add: SetStateItem) -> None: ...


class WithZeroStatus:
    # util: lets an activity raise the otherwise-trace opening status to a real level.
    level: ClassVar[int] = logging.INFO


# @runtime_checkable
class WithMessageParts(ABC):
    # core: contributes human-readable parts to the rendered message.
    def message_parts(self, append: AppendMessagePart) -> None: ...


class MessageSchema(ABC):
    @abc.abstractmethod
    def compose(self, state_items: dict[str, Any], *source: Any) -> str: ...


class _Forgiving(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"  # core: leave the hole visible rather than raise.


class CompactMessageSchema(MessageSchema):
    def __init__(self, separator: str = "; ") -> None:
        self._separator = separator

    def compose(self, state_items: dict[str, Any], *sources: Any) -> str:
        parts: list[str] = []

        def append(part: str) -> None:
            if part:
                parts.append(part)

        for item in sources:
            match item:
                case WithMessageParts() as source:
                    source.message_parts(append)

        template = self._separator.join(part for part in parts)
        return template.format_map(_Forgiving(state_items))


class CompactMessagePrefix(WithMessageParts):
    def message_parts(self, append: AppendMessagePart) -> None:
        append("{activity_role}: {activity}[{activity_status}]")
        append("Elapsed: {elapsed_ms} ms")


# core: marker roles. Empty bases checked with isinstance — never Protocol, because
# a methodless runtime_checkable Protocol matches every object and breaks the checks.
class ActivityStatusRole:
    class Last:
        ...

    class Veto:
        ...

    class User:
        ...

    class Auto:
        ...


class LastStatusCanBeVoid:
    pass


class LastStatusCanOverflow:
    pass


class AutoLogLastStatus:
    pass


class WithCompactMessageSchema:
    message_schema: ClassVar[MessageSchema] = CompactMessageSchema()


@dataclass(frozen=True)
class Activity(ABC):

    @property
    def name(self) -> str:
        return type(self).__qualname__

    @property
    @abc.abstractmethod
    def role(self) -> str: ...


class Core(Activity):
    role = "Core"


class Buzz(Activity):
    role = "Buzz"


@dataclass(frozen=True, slots=True)
class ActivityStatus[A: Activity]:
    # core: the phantom A binds a status to one activity type. It is consumed by
    # ActivityScope[A].log_status, which is what makes the type checker reject
    # logging activity X's status into a scope opened for activity Y.
    code: ClassVar[str]


def resolve_status_level[A: Activity](activity: Activity, status: ActivityStatus[A]) -> int:
    match status:
        case Zero():
            match activity:
                case WithZeroStatus():
                    return logging.INFO
                case _:
                    return logging.DEBUG
        case Void():
            return logging.INFO
        case Okay():
            return logging.INFO
        case Fail():
            return logging.ERROR
        case Last():
            match activity:
                case AutoLogLastStatus():
                    return logging.INFO
                case _:
                    return logging.WARNING
        case _:
            return logging.INFO


# ── core statuses (user-loggable) ────────────────────────────────────────────────

# core: the activity started but deliberately stops before its normal completion
# path because a known, non-exceptional condition makes continuation invalid.
@dataclass(frozen=True, slots=True)
class Halt[A: Activity](ActivityStatus[A], WithMessageParts, ActivityStatusRole.Last, ActivityStatusRole.Veto, ActivityStatusRole.User):
    code = "Halt"
    reason: str = state_item(default="Unspecified")

    def message_parts(self, append: AppendMessagePart) -> None:
        append("Reason: {reason}")


# core: everything went according to plan.
@dataclass(frozen=True, )
class Okay[A: Activity](ActivityStatus[A], ActivityStatusRole.Last, ActivityStatusRole.User):
    code = "Okay"


# core: an error occurred.
@dataclass(frozen=True)
class Fail[A: Activity](ActivityStatus[A], ActivityStatusRole.Last, ActivityStatusRole.User):
    code = "Fail"
    exception: Exception | None

    def message_parts(self, append: AppendMessagePart) -> None:
        if self.exception is not None:
            append(f"Exception: {str(self.exception)}")


# ── auto statuses (framework-logged) ─────────────────────────────────────────────

# note: the very first status. Its previous name was "First".
@dataclass(frozen=True)
class Zero[A: Activity](ActivityStatus[A], ActivityStatusRole.Auto):
    code = "Zero"


# core: emitted while the activity runs; carries an ad-hoc message. The level is a
# constructor argument now — debug/trace are factory methods, not subclasses.
@dataclass(frozen=True)
class Beep[A: Activity](ActivityStatus[A], ActivityStatusRole.Auto):
    code = "Beep"
    message: str

    def message_parts(self, append: AppendMessagePart) -> None:
        if self.message is not None:
            append(self.message)


# info/warn are factory methods; the message text follows from the level.
@dataclass(frozen=True)
class Void[A: Activity](ActivityStatus[A], WithMessageParts, ActivityStatusRole.Auto, ActivityStatusRole.Last):
    code = "Void"

    def message_parts(self, append: AppendMessagePart) -> None:
        append("CanBeVoid policy is set; it allows omitting an explicit last status.")


@dataclass(frozen=True)
class Last[A: Activity](ActivityStatus[A], WithMessageParts, ActivityStatusRole.Auto, ActivityStatusRole.Last):
    code = "Last"

    def message_parts(self, append: AppendMessagePart) -> None:
        append("An explicit last status is missing; using this as fallback.")


class ActivityScope[A: Activity]:
    _stack: ClassVar[ContextVar[ActivityScope[Any] | None]] = ContextVar("current_activity", default=None)
    message_schema: ClassVar[MessageSchema] = CompactMessageSchema()
    message_prefix: ClassVar[WithMessageParts] = CompactMessagePrefix()

    def __init__(self, activity: A, trace_id: Any | None, frame: FrameInfo | None = None) -> None:
        self._activity = activity
        self.trace_id: str = trace_id or secrets.token_hex(16)
        self.scope_id: str = secrets.token_hex(8)  # note: python reserves id already.
        self.parent: ActivityScope[Any] | None = None  # core: This is going to be set on __enter__.
        self.frame = frame
        self.stopwatch: Stopwatch = Stopwatch()
        self._last_index = LastIndex()
        self._logger: logging.Logger = logging.getLogger(activity.name)

    def __iter__(self) -> Iterator[ActivityScope[Any]]:
        current: ActivityScope[Any] | None = self
        while current:
            yield current
            current = current.parent

    @property
    def depth(self) -> int:
        return self.parent.depth + 1 if self.parent else 0

    @property
    def state_items(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "scope_id": self.scope_id,
            "parent_id": self.parent.scope_id if self.parent else None,
            "activity": self._activity.name,
            "activity_role": self._activity.role,
            "message_role": "Data",
            "elapsed_ms": self.stopwatch.elapsed_ms,
            "depth": self.depth,
        }

    @classmethod
    def begin(cls, activity: A, trace_id: Any | None, frame: FrameInfo | None) -> ActivityScope[A]:
        return cls(activity, trace_id, frame)

    def log_status(self, status: Beep[A] | Halt[A] | Okay[A] | Fail[A]) -> ActivityScope[A]:
        return self._log(status)

    def _log(self, status: ActivityStatus[A]) -> ActivityScope[A]:

        state_items: dict[str, Any] = self.state_items
        state_items |= {
            "activity_status": status.code,
        }
        state_items |= dump_state_items(self._activity)
        state_items |= dump_state_items(status)

        for item in [self._activity, status]:
            state_items |= dump_state_items(item)

        if isinstance(status, ActivityStatusRole.Last):
            self._last_index.increment()
            state_items |= self._last_index.to_dict()

        if self._last_index.overflows and not isinstance(self._activity, LastStatusCanOverflow):
            raise RuntimeError(f"Cannot log {status.code} for {self._activity.name} as it already logged one last status.")

        def set_state_item(key: str, value: Any) -> None:
            state_items[key] = value

        for item in [self._activity, status]:
            if isinstance(item, WithStateItems):
                item.state_items(set_state_item)

        message = self.message_schema.compose(state_items, self.message_prefix, self._activity, status)
        status_level = resolve_status_level(self._activity, status)
        if self._last_index.overflows:
            status_level = max(status_level, logging.WARNING)

        self._logger.log(status_level, message, extra={"wiretap": state_items})
        return self

    @classmethod
    def current(cls) -> ActivityScope[Any] | None:
        return cls._stack.get()

    def __enter__(self) -> ActivityScope[A]:
        if parent := ActivityScope._stack.get():
            self.parent = parent

        self._token = ActivityScope._stack.set(self)
        self._log(Zero())

        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if not self._last_index:
                if exc_type is not None:
                    self._log(Fail(exception=exc))
                else:
                    self._log(Last())
        finally:
            ActivityScope._stack.reset(self._token)
            self.parent = None


def begin_scope[A: Activity](activity: A, trace_id: Any | None = None) -> ActivityScope[A]:
    stack = inspect.stack(2)
    frame = stack[2]

    return ActivityScope.begin(activity, trace_id, frame)


# examples ---


def dump_state_items(obj: Any) -> dict[str, object]:
    if not is_dataclass(obj):
        return {}
    return {
        f.name: getattr(obj, f.name)
        for f in fields(obj)
        if f.metadata.get("state_item")
    }


@dataclass(frozen=True)
class Prototyping(Core):
    activity_name: str
    state: dict[str, Any] | None

    @dataclass(frozen=True)
    class Beep(Beep):
        message: str

    @dataclass(frozen=True)
    class Okay(Okay):
        message: str

    @dataclass(frozen=True)
    class Fail(Fail):
        message: str


def log_note(message: str) -> None:
    if scope := ActivityScope.current():
        state_items = scope.state_items
        logging.log(logging.INFO, message, extra={"wiretap": state_items})
    else:
        logging.log(logging.INFO, message)


def log_echo(message: str, *, level: Literal["info", "debug", "trace"] = "info") -> None:
    logging.log(level, message)
