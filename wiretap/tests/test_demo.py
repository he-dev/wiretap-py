"""Run only this example: python -m pytest wiretap/tests/test_demo.py -v."""

import json
import logging

import pytest

from wiretap import Wiretap
from wiretap.util.logging import JsonFormatter


class TestHandler(logging.Handler):
    """Collects raw records in memory instead of printing or writing them."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        # Python logging calls emit() for each record reaching this handler.
        self.records.append(record)


CapturedLogs = tuple[str, list[logging.LogRecord]]


@pytest.fixture
def captured(request: pytest.FixtureRequest) -> CapturedLogs:
    # indirect=["captured"] sends the parameterized log level to this fixture.
    level: int = request.param

    # The full test identifier includes its parameters, giving each case its own logger.
    name = request.node.nodeid
    logger = logging.getLogger(name)
    handler = TestHandler()
    logger.handlers = [handler]
    logger.setLevel(level)

    # Do not forward records to parent/root loggers and their application handlers.
    logger.propagate = False
    # Ensure this named logger is enabled, independently of its level threshold.
    logger.disabled = False

    # This return value becomes the test's "captured" argument.
    return name, handler.records


@pytest.fixture
def json_formatter() -> JsonFormatter:
    # Tests configure their own pipeline explicitly; no demo YAML or file handlers.
    return JsonFormatter(
        encoders=[],
        pipeline=[
            "wiretap.util.rendering.build_json.AddMessage",
            "wiretap.util.rendering.build_json.AddActivity",
            "wiretap.util.rendering.build_json.AddProperties",
            "wiretap.util.rendering.build_json.AddTrace",
        ],
    )


@pytest.mark.parametrize(
    ("captured", "expected_events"),
    [
        pytest.param(logging.DEBUG, ["ZERO", "TICK", "LAST"], id="debug"),
        pytest.param(logging.INFO, ["TICK", "LAST"], id="info"),
    ],
    # Only "captured" goes through a fixture; expected_events goes straight to the test.
    indirect=["captured"],
)
def test_activity_and_json_pipeline(
    captured: CapturedLogs,
    expected_events: list[str],
    json_formatter: JsonFormatter,
) -> None:
    name, records = captured

    # Match the activity name to the logger configured by the captured fixture.
    logger, wiretap = Wiretap.get(name)
    with wiretap.begin_scope(name, "regular", order_id=42) as activity:
        logger.debug(None, extra=activity.zero())
        logger.info("Working", extra=activity.tick(attempt=1))
        logger.info("Order {properties[order_id]} finished", extra=activity.last())

    # INFO filters ZERO, but the event must still advance the lifecycle.
    assert [record.activity["event"] for record in records] == expected_events
    assert all(record.activity["event"] != "BEEP" for record in records)

    # CaptureHandler stores raw records. Explicitly run them through the JSON pipeline.
    entries = [json.loads(json_formatter.format(record)) for record in records]
    assert entries[-1]["message"] == "Order 42 finished"
    assert entries[-1]["properties"] == {"order_id": 42}
    assert entries[-2]["properties"] == {"order_id": 42, "attempt": 1}
    assert entries[-1]["activity"]["duration_ms"] >= 0
    assert "diagnostics" not in entries[-1]["activity"]

    # All events in this activity must describe the same trace and span.
    assert all(entry["trace"] == entries[0]["trace"] for entry in entries)


@pytest.mark.parametrize("captured", [logging.INFO], indirect=True)
def test_invalid_sequence_is_reported(
    captured: CapturedLogs,
    json_formatter: JsonFormatter,
) -> None:
    name, records = captured

    logger, wiretap = Wiretap.get(name)
    with wiretap.begin_scope(name, "regular") as activity:
        logger.debug(None, extra=activity.zero())
        logger.info("Finished", extra=activity.last())
        # Repeating LAST is misuse, but it should still produce a log record.
        logger.info("Invalid sequence", extra=activity.last())

    assert [record.activity["event"] for record in records] == ["LAST", "BEEP", "LAST"]
    assert records[1].levelno == logging.ERROR
    assert records[1].properties["beep_code"] == "no-events-must-follow-last"

    # Framework findings are separate records using the affected activity's trace.
    entry = json.loads(json_formatter.format(records[1]))
    assert entry["activity"]["event"] == "BEEP"
    assert entry["properties"]["beep_code"] == "no-events-must-follow-last"
    assert entry["trace"] == records[-1].trace
