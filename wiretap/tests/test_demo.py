"""Run only this example: python -m pytest wiretap/tests/test_demo.py -v."""

import json
import logging

import pytest

from wiretap import begin_scope
from wiretap.util.logging import JsonFormatter


class CaptureHandler(logging.Handler):
    """Collect raw records in memory instead of printing or writing them."""

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
    handler = CaptureHandler()
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
            "wiretap.util.buzz.build_json.AddMessage",
            "wiretap.util.buzz.build_json.AddActivity",
            "wiretap.util.buzz.build_json.AddContext",
            "wiretap.util.buzz.build_json.AddTrace",
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
    with begin_scope(name, order_id=42) as activity:
        activity.zero.log_debug(None)
        activity.tick.log_info("Working", attempt=1)
        activity.last.log_info("Order {context[order_id]} finished")

    # INFO filters ZERO, but the event must still advance the lifecycle.
    assert [record.activity["event"] for record in records] == expected_events
    assert not records[-1].__dict__.get("fixme")

    # CaptureHandler stores raw records. Explicitly run them through the JSON pipeline.
    entries = [json.loads(json_formatter.format(record)) for record in records]
    assert entries[-1]["message"] == "Order 42 finished"
    assert entries[-1]["context"] == {"order_id": 42}
    assert entries[-2]["context"] == {"order_id": 42, "attempt": 1}
    assert entries[-1]["activity"]["duration_ms"] >= 0
    assert "fixme" not in entries[-1]

    # All events in this activity must describe the same trace and span.
    assert all(entry["trace"] == entries[0]["trace"] for entry in entries)


@pytest.mark.parametrize("captured", [logging.INFO], indirect=True)
def test_invalid_sequence_is_reported(
    captured: CapturedLogs,
    json_formatter: JsonFormatter,
) -> None:
    name, records = captured

    with begin_scope(name) as activity:
        activity.zero.log_debug(None)
        activity.last.log_info("Finished")
        # Repeating LAST is misuse, but it should still produce a log record.
        activity.last.log_info("Invalid sequence")

    assert len(records) == 2
    assert records[-1].fixme == ["last-must-occur-only-once"]

    # The record's fixme list is included in the JSON output.
    entry = json.loads(json_formatter.format(records[-1]))
    assert entry["fixme"] == ["last-must-occur-only-once"]
