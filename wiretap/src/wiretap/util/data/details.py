from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from wiretap.util.data.dotted_name import DottedName


class DetailCollection(OrderedDict[DottedName, Any | None]):
    # core: Details keep insertion order and preserve None until the final logging edge decides what to omit.
    pass


@dataclass
class DetailOptions:
    # core: Cascading controls whether a parent activity detail flows into descendant activity logs.
    cascade: bool = False
