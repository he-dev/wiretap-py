from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from wiretap.core.activity_status import Fail, Okay, Void
from wiretap.util.activity import Activity
from wiretap.util.activity_feed import PushMessagePart, PushStateItem


@dataclass  # (frozen=True)
class Buzz(Activity):
    must_log_zero: ClassVar[bool] = False
    can_log_void: ClassVar[bool] = False


@dataclass  # (frozen=True)
class Snap(Activity):
    pass


@dataclass
class PrototypeBuzz(Buzz):
    """
    A prototype buzz activity for testing and development purposes.
    """
    tags = ["prototype-buzz"]

    def __init__(self, name: str, message: str | None = None, **kwargs: Any) -> None:
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
        def __init__(self, message: str | None = None, **kwargs: Any) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, push: PushStateItem) -> None:
            for key, value in self._state.items():
                push(key, value)

        def message_parts(self, push: PushMessagePart) -> None:
            push(self._message)

    @dataclass
    class Okay(Okay["PrototypeBuzz"]):
        def __init__(self, message: str | None = None, **kwargs: Any) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, push: PushStateItem) -> None:
            for key, value in self._state.items():
                push(key, value)

        def message_parts(self, push: PushMessagePart) -> None:
            push(self._message)

    @dataclass
    class Fail(Fail["PrototypeBuzz"]):
        def __init__(self, message: str | None = None, **kwargs: Any) -> None:
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

    def __init__(self, name: str, message: str | None = None, **kwargs: Any) -> None:
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
        def __init__(self, message: str | None = None, **kwargs: Any) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, push: PushStateItem) -> None:
            for key, value in self._state.items():
                push(key, value)

        def message_parts(self, push: PushMessagePart) -> None:
            push(self._message)
