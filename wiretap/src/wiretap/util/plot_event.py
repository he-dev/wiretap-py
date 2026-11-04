from enum import auto, IntEnum


class PlotEvent(IntEnum):
    ZERO = auto()
    TICK = auto()
    LAST = auto()
    SNAP = auto()
