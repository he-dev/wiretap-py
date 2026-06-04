from typing import Iterable, Callable, Any


class PathOf[T]:
    def __init__(self, obj: Iterable[T], selector: Callable[[T], Any], separator: str = "/") -> None:
        self._obj = obj
        self._selector = selector
        self._separator = separator

    def __str__(self) -> str:
        names = [str(self._selector(item)) for item in self._obj]
        return self._separator.join(names)
