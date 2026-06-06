from dataclasses import dataclass
from typing import Any, ClassVar

from wiretap.util.activity import Activity
from wiretap.util.activity_feed import PushItem
import wiretap.core.activity_status as status


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

    def state_items(self, push: PushItem) -> None:
        for key, value in self._state.items():
            push(key, value)

    def message_parts(self, push: PushItem) -> None:
        push(None, self._message)

    @dataclass
    class Void(status.Void["PrototypeBuzz"]):
        def __init__(self, message: str | None = None, **kwargs: Any) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, push: PushItem) -> None:
            for key, value in self._state.items():
                push(key, value)

        def message_parts(self, push: PushItem) -> None:
            push(None, self._message)

    @dataclass
    class Okay(status.Okay["PrototypeBuzz"]):
        def __init__(self, message: str | None = None, **kwargs: Any) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, push: PushItem) -> None:
            for key, value in self._state.items():
                push(key, value)

        def message_parts(self, push: PushItem) -> None:
            push(None, self._message)

    @dataclass
    class Fail(status.Fail["PrototypeBuzz"]):
        def __init__(self, message: str | None = None, **kwargs: Any) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, push: PushItem) -> None:
            for key, value in self._state.items():
                push(key, value)

        def message_parts(self, push: PushItem) -> None:
            push(None, self._message)


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

    def state_items(self, push: PushItem) -> None:
        for key, value in self._state.items():
            push(key, value)

    def message_parts(self, push: PushItem) -> None:
        push(None, self._message)

    @dataclass
    class Okay(status.Okay["PrototypeSnap"]):
        def __init__(self, message: str | None = None, **kwargs: Any) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, push: PushItem) -> None:
            for key, value in self._state.items():
                push(key, value)

        def message_parts(self, push: PushItem) -> None:
            push(None, self._message)
