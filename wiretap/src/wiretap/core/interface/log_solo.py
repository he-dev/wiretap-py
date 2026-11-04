from typing import Literal

from wiretap.util.plot import SnapLogger


def snap(about: str, story: Literal["user", "buzz"]) -> SnapLogger:
    """Emits a snap event which is a self-contained plot."""
    return SnapLogger(about, story)
