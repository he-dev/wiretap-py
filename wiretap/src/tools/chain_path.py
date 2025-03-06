from typing import Iterable, TypeVar, Callable, Any

T = TypeVar("T", bound=Iterable)


class ChainPath:

    def __init__(self, obj: T, selector: Callable[[T], Any]):
        self.names: list[str] = [str(selector(x)) for x in obj][::-1]

    def __str__(self) -> str:
        return "/".join(self.names)
