import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Self

import pytest


@dataclass
class TestStatus:
    code: str
    role: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(**data)


@dataclass
class TestSource:
    func: str
    file: str
    line: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(**data)


@dataclass
class TestActivity:
    name: str
    path: str
    depth: int
    status: TestStatus
    tags: list[str]
    duration_ms: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(**(data | {
            "path": str(data["path"]),
            "status": TestStatus.from_dict(data["status"]),
        }))


@dataclass
class TestEntry:
    trace_id: str
    span_id: str
    parent_id: str | None
    activity: TestActivity
    state: dict[str, Any]
    source: TestSource

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(**(data | {
            "activity": TestActivity.from_dict(data["activity"]),
            "source": TestSource.from_dict(data["source"]),
        }))


@dataclass
class TestItem:
    record: logging.LogRecord
    wiretap: TestEntry

    @classmethod
    def from_record(cls, record: logging.LogRecord) -> Self:
        return cls(
            record=record,
            wiretap=TestEntry.from_dict(getattr(record, "wiretap")),
        )


class ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[TestItem] = []

    def emit(self, record: logging.LogRecord) -> None:
        if hasattr(record, "wiretap"):
            self.records.append(TestItem.from_record(record))


@pytest.fixture
def logs() -> Iterator[list[TestItem]]:
    handler = ListHandler()
    root = logging.getLogger()
    handlers = root.handlers[:]
    level = root.level

    root.handlers = [handler]
    root.setLevel(logging.DEBUG)

    try:
        yield handler.records
    finally:
        root.handlers = handlers
        root.setLevel(level)
