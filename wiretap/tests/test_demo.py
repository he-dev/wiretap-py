"""Run only this example: python -m pytest wiretap/tests/test_demo.py -v."""

import json
import logging

import pytest

from wiretap import Storyline
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
            "wiretap.util.buzz.build_json.AddPlot",
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
def test_plot_and_json_pipeline(
    captured: CapturedLogs,
    expected_events: list[str],
    json_formatter: JsonFormatter,
) -> None:
    name, records = captured

    # Match the plot name to the logger configured by the captured fixture.
    logger, storyline = Storyline.logger(name)
    with storyline.begin_plot(name, "core", order_id=42) as plot:
        logger.debug(None, extra=plot.zero())
        logger.info("Working", extra=plot.tick(attempt=1))
        logger.info("Order {context[order_id]} finished", extra=plot.last())

    # INFO filters ZERO, but the event must still advance the lifecycle.
    assert [record.plot["event"] for record in records] == expected_events
    assert not records[-1].plot["diagnostics"]["errors"]

    # CaptureHandler stores raw records. Explicitly run them through the JSON pipeline.
    entries = [json.loads(json_formatter.format(record)) for record in records]
    assert entries[-1]["message"] == "Order 42 finished"
    assert entries[-1]["context"] == {"order_id": 42}
    assert entries[-2]["context"] == {"order_id": 42, "attempt": 1}
    assert entries[-1]["plot"]["duration_ms"] >= 0
    assert entries[-1]["plot"]["diagnostics"]["errors"] == []

    # All events in this plot must describe the same trace and span.
    assert all(entry["trace"] == entries[0]["trace"] for entry in entries)


@pytest.mark.parametrize("captured", [logging.INFO], indirect=True)
def test_invalid_sequence_is_reported(
    captured: CapturedLogs,
    json_formatter: JsonFormatter,
) -> None:
    name, records = captured

    logger, storyline = Storyline.logger(name)
    with storyline.begin_plot(name, "core") as plot:
        logger.debug(None, extra=plot.zero())
        logger.info("Finished", extra=plot.last())
        # Repeating LAST is misuse, but it should still produce a log record.
        logger.info("Invalid sequence", extra=plot.last())

    assert len(records) == 2
    assert records[-1].plot["diagnostics"]["errors"] == ["no-events-must-follow-last"]

    # The record's nested diagnostics are included in the JSON output.
    entry = json.loads(json_formatter.format(records[-1]))
    assert entry["plot"]["diagnostics"]["errors"] == ["no-events-must-follow-last"]
