import wiretap
from conftest import TestItem, TestStatus


def test_can_capture_activity_records_in_memory(logs: list[TestItem]) -> None:
    with wiretap.begin_buzz(wiretap.QuickBuzz(name="ImportDocument", source="customers.csv")) as scope:
        scope.set_status(wiretap.QuickBuzz.Okay(message="Imported records.", records_saved=3))

    assert [item.wiretap.activity.status.code for item in logs] == ["ready", "okay"]

    final = logs[-1].wiretap
    assert final.activity.name == "ImportDocument"
    assert final.activity.status == TestStatus(code="okay", role="last")
    assert final.state == {
        "source": "customers.csv",
        "records_saved": 3,
    }
