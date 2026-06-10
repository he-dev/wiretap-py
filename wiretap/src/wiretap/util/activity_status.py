import logging
from dataclasses import dataclass
from typing import ClassVar, Any

from wiretap.util.activity import Activity


@dataclass
class ActivityStatus[A: Activity]:
    # core: The phantom A binds a status to one activity type.
    level: ClassVar[int] = logging.INFO
    role: ClassVar[str] = "none"

    @property
    def code(self) -> str:
        # meta: Gets the status code from the concrete subclass but nearest to ActivityStatus.
        for cls in type(self).__mro__:
            # note: Flags are derived directly from ActivityStatus.
            if cls.__base__ is ActivityStatus:
                return cls.__name__
        raise TypeError(f"Activity status code not found because {type(self).__qualname__} does not inherit : must inherit from {ActivityStatus.__qualname__}.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.lower(),
            "role": self.role,
        }
