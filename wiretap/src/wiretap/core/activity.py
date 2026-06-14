from dataclasses import dataclass
from typing import Any

from wiretap.util.activity import Bulk, Buzz, Snap, StatusLogPolicy
from wiretap.util.activity_feed import PushItem, PushItemOptions
import wiretap.core.activity_status as status


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
class QuickBulk(Bulk[QuickBuzz]):
    """
    A low-ceremony buzz activity for counted bulk telemetry.

    Quick bulk activities are soft contracts for loops and repeated work where
    the parent summary matters more than a dedicated hard contract.
    """
    tags = ["quick-bulk"]

    def __init__(
            self,
            name: str,
            message: str | None = None,
            item_status_log_policy: StatusLogPolicy = StatusLogPolicy.BOTH,
            **kwargs: Any
    ) -> None:
        self._name = name
        self._message = message
        self._state = kwargs
        self.item_status_log_policy = item_status_log_policy

    @property
    def name(self) -> str:
        return self._name

    def state_items(self, push: PushItem) -> None:
        for key, value in self._state.items():
            push(key, value)

    def message_parts(self, push: PushItem) -> None:
        push("Message", self._message, PushItemOptions(label=False))

    @dataclass
    class Okay(status.Okay["QuickBulk"]):
        """
        Quick final status for a bulk activity that completed on an expected path.
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
    class Fail(status.Fail["QuickBulk"]):
        """
        Quick final status for a bulk activity that failed.
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
