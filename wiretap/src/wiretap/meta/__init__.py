import itertools
import pathlib
from collections import deque
from enum import Enum
from typing import TypeVar, Optional, Iterable, Generator, Any

T = TypeVar('T')


def nth_or_default_(source: list[T], index: int) -> Optional[T]:
    return source[index] if index < len(source) else None


def nth_or_default(source: Iterable[T], index: int, default: Optional[T] = None) -> Optional[T]:
    return next(itertools.islice(source, index, None), default)


def fast_reverse(iterable: Iterable[T]) -> Generator[T, None, None]:
    stack = deque(iterable, maxlen=None)
    while stack:
        yield stack.pop()


class LowerEnum(Enum):
    def __str__(self):
        return self.name.lower()

    def __repr__(self):
        return str(self)


class KebabEnum(Enum):
    """ Converts a snake_case string to a kebab-case string. """

    def __str__(self):
        return self.name.lower().replace('_', '-').lower()

    def __repr__(self):
        return str(self)


def trim_path(
        path: str,
        before: tuple[str, ...] = ("src", "app", "lib"),
        after: tuple[str, ...] = (),
) -> str:
    """Cut a path down to its meaningful tail.

    Tries to cut at `after` first and falls back to `before` otherwise; the
    match nearest the file wins. Useful for shortening paths and for hiding
    local prefixes, so logs don't reveal where the code lives on disk.

    Args:
        path: The path to trim.
        after: Separators that cut *after* themselves — the matched segment and
            everything before it are dropped. This is the hiding cut: whatever
            you name here never appears in the result.
        before: Separators that cut *before* themselves — the matched segment is
            kept, along with everything after it. Only used when no `after`
            separator matched. Can only ever cut sooner than `after` would, so
            it makes the path stricter (shorter), never longer.

    Returns:
        The trimmed path as a /-joined POSIX string, regardless of host OS. If
        neither separator matches, the whole path is returned unchanged.
    """

    # core: Drop the private prefix and keep the meaningful tail from the nearest anchor.
    parts = pathlib.Path(path).parts

    # core: Default to the whole path; nothing to cut against until a separator matches.
    start = 0

    # note: Walk indices backwards.
    # note: start: last valid index, because indices are zero-based.
    # note: stop: range stops one BEFORE its stop, so -1 lets index 0 be visited.
    # note: step: walk backwards so the FIRST match is the anchor nearest the file.
    for index in range(len(parts) - 1, -1, -1):
        # core: `after` has precedence: drop the matched separator and everything before it.
        if parts[index] in after:
            start = index + 1
            break
        # core: `before` only counts where `after` did not match; keep the matched separator onward.
        if parts[index] in before:
            start = index
            break

    # core: No anchor matched, so there is nothing to trim against; return the path unchanged.
    # meta: PurePosixPath instead of Path so the output is always /-joined regardless of host OS.
    return pathlib.PurePosixPath(*parts[start:]).as_posix()


def stringify_deep(obj: dict | Any) -> dict | str:
    match obj:
        case dict():
            return {k: stringify_deep(v) for k, v in obj.items()}
        case _:
            return str(obj)
