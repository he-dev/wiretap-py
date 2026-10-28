import logging

from wiretap.core.objective.log_event import log_event


# note: Ignore duplicate code for the below functions because they are too small to refactor.

# noinspection DuplicatedCode
def log_debug(message: str | None = None, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level=logging.DEBUG, state=state, **kwargs)


# noinspection DuplicatedCode
def log_info(message: str, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level=logging.INFO, state=state, **kwargs)


# noinspection DuplicatedCode
def log_warning(message: str, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level=logging.WARNING, state=state, **kwargs)


# noinspection DuplicatedCode
def log_error(message: str, state: dict | None = None, **kwargs) -> None:
    log_event(message=message, level=logging.ERROR, state=state, **kwargs)
