import contextlib
from typing import Iterator, Literal

from wiretap.util.activity import ActivityAbout


@contextlib.contextmanager
def log_envelope(
        activity: ActivityAbout,
        mode: Literal["auto", "zero_only", "last_only"] = "auto",
        **kwargs
) -> Iterator[None]:
    # meta: Account for the nesting of the log_envelope context manager by adjusting the stack-level.

    if mode in ("auto", "zero_only"):
        activity.zero.log_debug(None, stack_level=5, **kwargs)

    try:
        yield
    except Exception:
        if mode in ("auto", "last_only"):
            activity.last.log_error(None, stack_level=5, **kwargs)
        raise
    else:
        if mode in ("auto", "last_only"):
            activity.last.log_info(None, stack_level=5, **kwargs)
