from enum import auto, IntEnum


class ActivityEvent(IntEnum):
    ZERO = auto()
    TICK = auto()
    LAST = auto()
    SNAP = auto()
    BEEP = auto()
