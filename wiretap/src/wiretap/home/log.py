from wiretap.core.span import Span


# node: Ignore duplicate code in these functions because they are too small to refactor.

# noinspection DuplicatedCode
def log_info(message: str, state: dict | None = None, **kwargs) -> None:
    Span.log_event(message=message, level="info", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_debug(message: str, state: dict | None = None, **kwargs) -> None:
    Span.log_event(message=message, level="debug", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_trace(message: str, state: dict | None = None, **kwargs) -> None:
    Span.log_event(message=message, level="trace", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_warning(message: str, state: dict | None = None, **kwargs) -> None:
    Span.log_event(message=message, level="warning", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_error(message: str, state: dict | None = None, **kwargs) -> None:
    Span.log_event(message=message, level="error", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)


# noinspection DuplicatedCode
def log_critical(message: str, state: dict | None = None, **kwargs) -> None:
    Span.log_event(message=message, level="critical", state=state, frame_at=kwargs.pop("frame_at", 2), **kwargs)
