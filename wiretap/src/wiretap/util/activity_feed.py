import logging
from dataclasses import dataclass
from functools import cache
from typing import Any, Protocol, runtime_checkable

from wiretap.meta.annotations import _annotated_fields
from wiretap.util.annotations import Remark, Detail

# util: Internal logger.
_logger = logging.getLogger("wiretap")


@dataclass(frozen=True)
class PushItemOptions:
    label: bool = True
    separator: str | None = ": "


class PushItem(Protocol):
    # util: Common feed sink for both structured details and remarks.
    def __call__(self, name: str, value: Any, options: PushItemOptions | None = None) -> None: ...


class PushDetail(PushItem, Protocol):
    # core: Feeds structured log properties.
    pass


@runtime_checkable
class DetailSource(Protocol):
    # core: Feeds structured properties to the log scope.
    def details(self, push: PushDetail) -> None: ...


@runtime_checkable
class RemarkSource(Protocol):
    # core: Feeds human-readable remarks to the rendered message.
    def remarks(self, push: PushItem) -> None: ...


# core: Warns about conflicting annotations between a class and a protocol.
@cache
def _warn_if_protocol_shadows_annotations(cls: type, protocol: type, annotation: type) -> None:
    if _annotated_fields(cls).get(annotation):
        _logger.warning(
            "%s uses the %s protocol which has precedence over field annotations %s that are also used.",
            cls.__qualname__, protocol.__name__, annotation.__name__,
        )


def collect_details(source: object, push_log_property: PushDetail) -> None:
    annotations = _annotated_fields(type(source)).get(Detail, {})  # type: ignore[arg-type]
    if isinstance(source, DetailSource):
        source.details(push_log_property)
        _warn_if_protocol_shadows_annotations(type(source), DetailSource, Detail)
    else:
        for name, annotation in annotations.items():
            detail: Detail = annotation
            push_log_property(name, getattr(source, name, detail.default_value))


def collect_details_cascading(source: object, push: PushDetail) -> None:
    annotations = _annotated_fields(type(source)).get(Detail, {})  # type: ignore[arg-type]
    for name, annotation in annotations.items():
        detail: Detail = annotation
        if detail.cascade:
            push(name, getattr(source, name, detail.default_value))


def collect_remarks(source: object, push: PushItem) -> None:
    annotations = _annotated_fields(type(source)).get(Remark, {})  # type: ignore[arg-type]
    if isinstance(source, RemarkSource):
        source.remarks(push)
        _warn_if_protocol_shadows_annotations(type(source), RemarkSource, Remark)
    else:
        for name, annotation in annotations.items():
            remark: Remark = annotation
            push(remark.label or name.capitalize(), getattr(source, name, None))
