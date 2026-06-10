from dataclasses import dataclass
from typing import Any, ClassVar

from wiretap.util.activity import Activity
from wiretap.util.activity_feed import PushItem, PushItemOptions
import wiretap.core.activity_status as status

_WITH_ZERO_STATUS = "__wiretap_with_zero_status__"


def with_zero_status[A: type](activity_type: A) -> A:
    setattr(activity_type, _WITH_ZERO_STATUS, True)
    return activity_type


def has_zero_status(activity: object) -> bool:
    return bool(getattr(type(activity), _WITH_ZERO_STATUS, False))


@dataclass
class Buzz(Activity):
    # must_log_zero: ClassVar[bool] = False
    pass


@dataclass
class Snap(Activity):
    pass


@dataclass
class QuickBuzz(Buzz):
    """
    A low-ceremony buzz activity for runtime-shaped telemetry.

    Quick activities are soft contracts. They let callers choose an activity
    name, optional message, and arbitrary state items without defining a hard
    activity/status contract first.
    """
    tags = ["quick-buzz"]

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
        push("Message", self._message, PushItemOptions(label=False))

    @dataclass
    class Void(status.Void["QuickBuzz"]):
        """
        Quick final status for a buzz whose outcome is intentionally unknown.
        """

        def __init__(self, message: str | None = None, **kwargs: Any) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, push: PushItem) -> None:
            for key, value in self._state.items():
                push(key, value)

        def message_parts(self, push: PushItem) -> None:
            push("Message", self._message, PushItemOptions(label=False))

    @dataclass
    class Okay(status.Okay["QuickBuzz"]):
        """
        Quick final status for a buzz that completed on an expected path.
        """

        def __init__(self, message: str | None = None, **kwargs: Any) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, push: PushItem) -> None:
            for key, value in self._state.items():
                push(key, value)

        def message_parts(self, push: PushItem) -> None:
            push("Message", self._message, PushItemOptions(label=False))

    @dataclass
    class Fail(status.Fail["QuickBuzz"]):
        """
        Quick final status for a buzz that failed.
        """

        def __init__(self, message: str | None = None, **kwargs: Any) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, push: PushItem) -> None:
            for key, value in self._state.items():
                push(key, value)

        def message_parts(self, push: PushItem) -> None:
            push("Message", self._message, PushItemOptions(label=False))


@dataclass
class QuickSnap(Snap):
    """
    A low-ceremony snap activity for runtime-shaped telemetry.

    Quick snaps are the instantaneous counterpart to QuickBuzz. They are useful
    when a dedicated Snap contract would add noise before the event shape is
    worth naming as a hard contract.
    """
    tags = ["quick-snap"]

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
        push("Message", self._message, PushItemOptions(label=False))

    @dataclass
    class Okay(status.Okay["QuickSnap"]):
        """
        Quick status for a snap that records an expected event.
        """

        def __init__(self, message: str | None = None, **kwargs: Any) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, push: PushItem) -> None:
            for key, value in self._state.items():
                push(key, value)

        def message_parts(self, push: PushItem) -> None:
            push("Message", self._message, PushItemOptions(label=False))

    @dataclass
    class Noop(status.Noop["QuickSnap"]):
        """
        Quick status for a snap that intentionally did nothing.
        """

        def __init__(self, message: str | None = None, **kwargs: Any) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, push: PushItem) -> None:
            for key, value in self._state.items():
                push(key, value)

        def message_parts(self, push: PushItem) -> None:
            push("Message", self._message, PushItemOptions(label=False))

    @dataclass
    class Fail(status.Fail["QuickSnap"]):
        """
        Quick status for a snap that failed.
        """

        def __init__(self, message: str | None = None, **kwargs: Any) -> None:
            self._message = message
            self._state = kwargs

        def state_items(self, push: PushItem) -> None:
            for key, value in self._state.items():
                push(key, value)

        def message_parts(self, push: PushItem) -> None:
            push("Message", self._message, PushItemOptions(label=False))
