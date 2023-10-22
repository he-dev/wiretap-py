import logging

from ..types import current_logger, ContextExtra


class AddContextExtra(logging.Filter):
    def __init__(self):
        super().__init__("context")

    def filter(self, record: logging.LogRecord) -> bool:
        logger = current_logger.get()
        context_extra = ContextExtra(
            parent_id=logger.parent.id if logger and logger.parent else None,
            unique_id=logger.id if logger else None,
            subject=logger.value.subject if logger else record.module,
            activity=logger.value.activity if logger else record.funcName
        )
        extra = vars(context_extra)
        for k, v in extra.items():
            record.__dict__[k] = v

        return True
