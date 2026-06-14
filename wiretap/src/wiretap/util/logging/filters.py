import logging
from typing import Iterable


class _StatusFilter(logging.Filter):
    def __init__(
            self,
            enabled: bool = True,
            code_in: Iterable[str] | None = None,
            role_in: Iterable[str] | None = None,
    ) -> None:
        super().__init__()
        self.enabled = enabled
        self._codes = {code.lower() for code in code_in} if code_in else None
        self._roles = {role.lower() for role in role_in} if role_in else None

    def matches(self, record: logging.LogRecord) -> bool:
        data = record.__dict__.get("wiretap", {})
        if not data:
            return False

        status = data.get("activity", {}).get("status")
        if not status:
            return False

        code = str(status.get("code", "")).lower()
        if self._codes is not None and code not in self._codes:
            return False

        role = str(status.get("role", "")).lower()
        if self._roles is not None and role not in self._roles:
            return False

        return True


class IncludeByStatus(_StatusFilter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not self.enabled or self.matches(record)


class ExcludeByStatus(_StatusFilter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not self.enabled or not self.matches(record)
