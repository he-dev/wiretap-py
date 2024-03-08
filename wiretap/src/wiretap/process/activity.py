import inspect
import logging
import re

from .elapsed import Elapsed


class Activity:
    """
    This class represents an activity for which telemetry is collected.
    """

    def __init__(
            self,
            name: str,
            frame: inspect.FrameInfo
    ):
        self.name = name
        self.frame = frame
        self.elapsed = Elapsed()
        self.is_open = OneTimeFlag(True)
        self.logger = logging.getLogger(name)


class OneTimeFlag:
    def __init__(self, initial_value: bool = False) -> None:
        self.state = initial_value
        self._initial_value = initial_value

    def __bool__(self):
        try:
            return self.state
        finally:
            if self.state == self._initial_value:
                self.state = not self.state


class TraceNameByCaller:

    def __init__(self, frame_index: int):
        caller = inspect.stack()[frame_index].function
        self.value = re.sub("^trace_", "", caller, flags=re.IGNORECASE)

    def __str__(self):
        return self.value
