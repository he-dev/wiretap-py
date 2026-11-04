from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TraceW3C:
    id: str
    span_id: str
    parent_id: str | None

    @classmethod
    def create(
            cls,
            trace_id: str | None = None,
            parent_id: str | None = None,
    ) -> TraceW3C:
        if trace_id is None:
            trace_id = secrets.token_hex(16)
        else:
            cls._validate_id(trace_id, 32, "trace_id")

        if parent_id is not None:
            cls._validate_id(parent_id, 16, "parent_id")

        return cls(id=trace_id, span_id=secrets.token_hex(8), parent_id=parent_id)

    @staticmethod
    def _validate_id(value: str, length: int, name: str) -> None:
        if not isinstance(value, str) or re.fullmatch(rf"[0-9a-f]{{{length}}}", value) is None:
            raise ValueError(f"{name} must be {length} lowercase hex characters")
        if value == "0" * length:
            raise ValueError(f"{name} must not be all zeros")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
        }
