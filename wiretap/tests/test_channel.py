import logging

from wiretap import Wiretap
from wiretap.core.activity_scope import ActivityScope


def test_custom_channel_flows_through_events_and_snap() -> None:
    _, wiretap = Wiretap.get(__name__)

    with wiretap.begin_scope("payment", "billing") as activity:
        assert activity.zero("audit")["activity"]["channel"] == "audit"
        assert activity.tick()["activity"]["channel"] == "billing"
        assert "channel" not in activity.tick()
        assert activity.last("audit")["activity"]["channel"] == "audit"
        assert wiretap.snap("check", "audit")["activity"]["channel"] == "audit"
        assert "channel" not in wiretap.snap("check", "audit")


def test_different_channels_share_context_and_restore_it() -> None:
    _, default = Wiretap.get(__name__)
    _, custom = Wiretap.get(__name__)

    with default.begin_scope("outer", "official", order_id=42) as outer:
        outer.zero()
        with custom.begin_scope("inner", "audit") as inner:
            inner.zero()
            snapshot = custom.snap("check", "audit")
            assert snapshot["properties"]["order_id"] == 42
            assert snapshot["activity"]["depth"] == 2
            assert inner.trace.id == outer.trace.id
            inner.last()
        current = ActivityScope.get_current()
        assert current is not None and current.about == "outer"
        outer.last()

    assert ActivityScope.get_current() is None


def test_framework_diagnostics_use_internal_channel(caplog) -> None:
    logger, wiretap = Wiretap.get(__name__)

    with caplog.at_level(logging.DEBUG, logger=logger.name):
        with wiretap.begin_scope("check", "audit") as activity:
            activity.zero()
            activity.last()
            activity.last()

    diagnostic, = [record for record in caplog.records if record.activity["event"] == "BEEP"]
    assert diagnostic.activity["channel"] == "internal"
    assert diagnostic.properties["beep_code"] == "no-events-must-follow-last"
