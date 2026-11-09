from types import MappingProxyType

import pytest

from wiretap import Wiretap
from wiretap.util.buzz.merge_properties import merge_properties


def test_merge_precedence_and_input_preservation():
    first = {"value": 1, "keep": True}
    second = MappingProxyType({"value": 2})
    assert merge_properties(first, second, value=3) == {"value": 3, "keep": True}
    assert first == {"value": 1, "keep": True}
    assert merge_properties() == {}
    assert merge_properties(value=3) == {"value": 3}


def test_rejects_non_mapping_properties():
    with pytest.raises(TypeError, match="must be mappings"):
        merge_properties("invalid")


def test_scope_and_snap_merge_properties_and_keep_trace_parameters_separate():
    _, wiretap = Wiretap.get(__name__)
    trace_id = "1" * 32
    parent_id = "2" * 16
    with wiretap.begin_scope(
        "scope", {"value": 1, "inherited": True}, value=2,
        trace_id=trace_id, parent_id=parent_id,
    ) as activity:
        activity.zero()
        assert activity.trace.id == trace_id
        extra = wiretap.snap("snap", {"value": 3}, {"other": 4}, value=5)
        assert extra["properties"] == {"value": 5, "inherited": True, "other": 4}
        assert wiretap.snap("snap")["properties"]["value"] == 2
        activity.last()

    with wiretap.begin_scope("no-mappings", trace_id=trace_id) as activity:
        activity.zero()
        assert activity.trace.id == trace_id
        activity.last()


def test_all_events_merge_properties_and_diagnostics_receive_them(caplog):
    logger, wiretap = Wiretap.get(__name__)
    with wiretap.begin_scope("scope", {"inherited": True}) as activity:
        for name in ("zero", "tick", "last"):
            extra = getattr(activity, name)({"value": 1}, {"value": 2}, value=3)
            assert extra["properties"] == {"inherited": True, "value": 3}
        with caplog.at_level("ERROR", logger=logger.name):
            activity.tick({"diagnostic": True}, value=4)
        assert caplog.records[-1].properties["diagnostic"] is True
        assert caplog.records[-1].properties["value"] == 4


@pytest.mark.parametrize("method", ["zero", "tick", "last"])
def test_events_reject_non_mapping_properties(method):
    _, wiretap = Wiretap.get(__name__)
    with wiretap.begin_scope("scope") as activity:
        with pytest.raises(TypeError, match="must be mappings"):
            getattr(activity, method)("invalid")
        activity.zero()
        activity.last()
