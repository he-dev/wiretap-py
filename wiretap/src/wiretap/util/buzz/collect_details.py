from typing import Any

from wiretap.meta.annotations import _annotated_fields
from wiretap.util.annotations import Detail
from wiretap.util.data import DetailBuilder, DetailOptions, DetailSource, DottedName


def collect_details(builder: DetailBuilder, source: object) -> None:
    # core: Protocol sources win over annotations because they are the more explicit contract.
    if isinstance(source, DetailSource):
        source.details(builder)

    # meta: Annotation discovery stays separate from collection so reflection can be cached later.
    for name, annotation in _annotated_fields(type(source)).get(Detail, {}).items():
        value = getattr(source, name, annotation.default_value)
        builder.add(DottedName(name), value, options=_options(annotation))


def _options(annotation: Any) -> DetailOptions:
    return DetailOptions(
        cascade=getattr(annotation, "cascade", False),
    )
