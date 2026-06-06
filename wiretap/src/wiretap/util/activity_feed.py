import logging
from functools import cache
from typing import Any, Callable, Protocol, runtime_checkable

from wiretap.core.annotations import FeedToMessagePart, FeedToStateItem
from wiretap.meta.annotations import _annotated_fields

# util: Internal logger.
_logger = logging.getLogger("wiretap")

type PushMessagePart = Callable[[str | None], None]
type PushStateItem = Callable[[str, Any], None]


@runtime_checkable
class StateItemFeed(Protocol):
    # core: Feeds structured fields to the log scope.
    def state_items(self, push: PushStateItem) -> None: ...


@runtime_checkable
class MessagePartFeed(Protocol):
    # core: Feeds human-readable parts to the rendered message.
    def message_parts(self, push: PushMessagePart) -> None: ...


# core: Warns about conflicting annotations between a class and a protocol.
@cache
def _warn_if_protocol_shadows_annotations(cls: type, protocol: type, annotation: type) -> None:
    if _annotated_fields(cls).get(annotation):
        _logger.warning(
            "%s uses the %s protocol which has precedence over field annotations %s that are also used.",
            cls.__qualname__, protocol.__name__, annotation.__name__,
        )


def get_state_items(source: object, push_state_item: PushStateItem) -> None:
    annotations = _annotated_fields(type(source)).get(FeedToStateItem, {})  # type: ignore[arg-type]
    if isinstance(source, StateItemFeed):
        source.state_items(push_state_item)
        _warn_if_protocol_shadows_annotations(type(source), StateItemFeed, FeedToStateItem)
    else:
        for name, annotation in annotations.items():
            state_item: FeedToStateItem = annotation
            push_state_item(name, getattr(source, name, state_item.default_value))


def get_state_items_cascading(source: object, push: PushStateItem) -> None:
    annotations = _annotated_fields(type(source)).get(FeedToStateItem, {})  # type: ignore[arg-type]
    for name, annotation in annotations.items():
        state_item: FeedToStateItem = annotation
        if state_item.cascade:
            push(name, getattr(source, name, state_item.default_value))


def get_message_parts(source: object, push: PushMessagePart) -> None:
    annotations = _annotated_fields(type(source)).get(FeedToMessagePart, {})  # type: ignore[arg-type]
    if isinstance(source, MessagePartFeed):
        source.message_parts(push)
        _warn_if_protocol_shadows_annotations(type(source), MessagePartFeed, FeedToMessagePart)
    else:
        for name, annotation in annotations.items():
            message_part: FeedToMessagePart = annotation
            push(f"{message_part.label or name.capitalize()}: {getattr(source, name, None)}")


class MessageHeaderFeed(MessagePartFeed):
    def message_parts(self, push: PushMessagePart) -> None:
        push("{activity[name]}[{activity[status]}]")
        push("Elapsed: {activity[elapsed_ms]} ms")
