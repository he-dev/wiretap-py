import dataclasses
import uuid
from typing import Optional, Iterator, TypeVar, Generic

_T = TypeVar("_T")


@dataclasses.dataclass
class Node(Generic[_T]):
    value: _T
    parent: Optional["Node[_T]"]
    id: uuid.UUID = dataclasses.field(default=uuid.uuid4())

    @property
    def depth(self) -> int:
        return self.parent.depth + 1 if self.parent else 1

    def __iter__(self) -> Iterator["Node"]:
        current: Node[_T] | None = self
        while current:
            yield current
            current = current.parent
