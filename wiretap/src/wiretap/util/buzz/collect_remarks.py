from typing import Any

from wiretap.meta.annotations import _annotated_fields
from wiretap.util.annotations import Remark
from wiretap.util.data import DottedName, QuoteMode, QuoteStyle, RemarkBuilder, RemarkOptions, RemarkSource


def collect_remarks(builder: RemarkBuilder, source: object) -> None:
    # core: Protocol sources win over annotations because they are the more explicit contract.
    if isinstance(source, RemarkSource):
        source.remarks(builder)

    # meta: Annotation discovery stays separate from collection so reflection can be cached later.
    for name, annotation in _annotated_fields(type(source)).get(Remark, {}).items():
        value = getattr(source, name, None)
        builder.add(DottedName(name), value, options=_options(annotation))


def _options(annotation: Any) -> RemarkOptions:
    return RemarkOptions(
        label=getattr(annotation, "label", None),
        separator=getattr(annotation, "separator", ": "),
        format=getattr(annotation, "format", None),
        quote_style=getattr(annotation, "quote_style", QuoteStyle.DOUBLE),
        quote_mode=getattr(annotation, "quote_mode", QuoteMode.NEVER),
    )
