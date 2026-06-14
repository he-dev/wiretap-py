import logging
from dataclasses import dataclass
from functools import cache
from typing import Any, Protocol, runtime_checkable

from wiretap.meta.annotations import _annotated_fields
from wiretap.util.annotations import FeedToMessagePart, FeedToStateItem

# util: Internal logger.
_logger = logging.getLogger("wiretap")


@dataclass(frozen=True)
class PushItemOptions:
    label: bool = True
    separator: str | None = ": "


class PushItem(Protocol):
    # util: Common feed sink for both structured state items and message parts.
    def __call__(self, name: str, value: Any, options: PushItemOptions | None = None) -> None: ...


@runtime_checkable
class StateItemFeed(Protocol):
    # core: Feeds structured fields to the log scope.
    def state_items(self, push: PushItem) -> None: ...


@runtime_checkable
class MessagePartFeed(Protocol):
    # core: Feeds human-readable parts to the rendered message.
    def message_parts(self, push: PushItem) -> None: ...


# core: Warns about conflicting annotations between a class and a protocol.
@cache
def _warn_if_protocol_shadows_annotations(cls: type, protocol: type, annotation: type) -> None:
    if _annotated_fields(cls).get(annotation):
        _logger.warning(
            "%s uses the %s protocol which has precedence over field annotations %s that are also used.",
            cls.__qualname__, protocol.__name__, annotation.__name__,
        )


def get_state_items(source: object, push_state_item: PushItem) -> None:
    annotations = _annotated_fields(type(source)).get(FeedToStateItem, {})  # type: ignore[arg-type]
    if isinstance(source, StateItemFeed):
        source.state_items(push_state_item)
        _warn_if_protocol_shadows_annotations(type(source), StateItemFeed, FeedToStateItem)
    else:
        for name, annotation in annotations.items():
            state_item: FeedToStateItem = annotation
            push_state_item(name, getattr(source, name, state_item.default_value))


def get_state_items_cascading(source: object, push: PushItem) -> None:
    annotations = _annotated_fields(type(source)).get(FeedToStateItem, {})  # type: ignore[arg-type]
    for name, annotation in annotations.items():
        state_item: FeedToStateItem = annotation
        if state_item.cascade:
            push(name, getattr(source, name, state_item.default_value))


def get_message_parts(source: object, push: PushItem) -> None:
    annotations = _annotated_fields(type(source)).get(FeedToMessagePart, {})  # type: ignore[arg-type]
    if isinstance(source, MessagePartFeed):
        source.message_parts(push)
        _warn_if_protocol_shadows_annotations(type(source), MessagePartFeed, FeedToMessagePart)
    else:
        for name, annotation in annotations.items():
            message_part: FeedToMessagePart = annotation
            push(message_part.label or name.capitalize(), getattr(source, name, None))
