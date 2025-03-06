import logging
from typing import Any

from wiretap.data import TagSet
from wiretap.scopes import TelemetryItem
from wiretap.scopes.telemetry_scope import TelemetryScope, TelemetryTrace


class Telemetry:
    """
    This class represents a procedure for which telemetry is collected.
    """

    def __init__(self, scope: TelemetryScope | None = None):
        scope = scope or TelemetryScope.peek()
        if not scope:
            raise Exception("Cannot create Telemetry without scope and neither one was passed nor is one in scope.")
        self.scope = scope
        self.can_log = True

    def log_trace(
            self,
            name: str,
            message: str | None = None,
            state: dict | None = None,
            tags: set[Any] | None = None,
            level: int = logging.DEBUG,
            exc_info: bool = False,
            is_final: bool = False,
            **kwargs
    ) -> None:
        """This function logs a single trace."""

        # Can no longer log.
        if not self.can_log:
            # Ignore logs from other final logs.
            if is_final:
                return
            # Logging non-final logs is otherwise illegal.
            else:
                raise Exception(f"The current scope '{self.scope.name}' can no longer log.")

        self.scope.log_trace(
            level=level,
            msg=message,
            exc_info=exc_info,
            extra=TelemetryItem(
                scope=self.scope,
                trace=TelemetryTrace(
                    name=name,
                    message=message,
                    state=(state or {}) | kwargs,
                    tags=TagSet(tags),
                    is_final=is_final,
                )
            )
        )

        if is_final:
            self.can_log = False

    def log_info(
            self,
            name: str = "info",
            message: str | None = None,
            state: dict | None = None,
            tags: set[Any] | None = None,
            is_final: bool = False,
            **kwargs
    ) -> None:
        """This function logs some additional information."""
        self.log_trace(
            name,
            message=message,
            state=state,
            tags=tags,
            level=logging.INFO,
            is_final=is_final,
            **kwargs
        )

    def log_debug(
            self,
            name: str = "debug",
            message: str | None = None,
            state: dict | None = None,
            tags: set[Any] | None = None,
            is_final: bool = False,
            **kwargs
    ) -> None:
        """This function logs some additional information."""
        self.log_trace(
            name=name,
            message=message,
            state=state,
            tags=tags,
            level=logging.DEBUG,
            is_final=is_final,
            **kwargs
        )

    def log_error(
            self,
            message: str | None = None,
            state: dict | None = None,
            tags: set[Any] | None = None,
            **kwargs
    ) -> None:
        """This function logs an error in the procedure."""
        self.log_trace(
            name="error",
            message=message,
            state=state,
            tags=(tags or set()),
            level=logging.ERROR,
            is_final=True, **kwargs
        )

    def log_exception(
            self,
            state: dict | None = None,
            tags: set[Any] | None = None,
    ) -> None:
        """This function logs an error in the procedure."""
        self.log_trace(
            name="exception",
            tags=tags,
            state=state,
            level=logging.CRITICAL,
            exc_info=True,
            is_final=True
        )
