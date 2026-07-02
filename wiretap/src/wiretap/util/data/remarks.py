from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum

from wiretap.util.data.dotted_name import DottedName


class RemarkCollection(OrderedDict[DottedName, str | None]):
    # core: Remarks are keyed so arrangement can pop known positions and leave the rest in insertion order.
    pass


class QuoteStyle(Enum):
    DOUBLE = "double"
    SINGLE = "single"


class QuoteMode(Enum):
    # util: Quote mode is independent of quote style so automatic whitespace quoting stays configurable.
    NEVER = "never"
    AUTO = "auto"
    ALWAYS = "always"


@dataclass
class RemarkOptions:
    # core: Remark options describe rendering; callers pass this object instead of growing method parameters.
    label: str | None = None
    separator: str = ": "
    format: str | None = None
    quote_style: QuoteStyle = QuoteStyle.DOUBLE
    quote_mode: QuoteMode = QuoteMode.NEVER
