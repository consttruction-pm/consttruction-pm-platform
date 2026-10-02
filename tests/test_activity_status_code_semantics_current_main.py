import pytest

from construction_pm.scheduling.activity import Activity, ActivityStatusCode


def test_activity_status_code_matches_p6_semantic_values() -> None:
    assert [item.value for item in ActivityStatusCode] == [
        "Planned",
        "Active",
        "Inactive",
        "What-If",
        "Requested",
        "Template",
    ]


def test_activity_status_code_is_typed_on_activity() -> None:
    activity = Activity(id="A-1", duration=1)
    assert activity.status_code is ActivityStatusCode.PLANNED

    with pytest.raises(TypeError, match="status_code"):
        Activity(id="A-1", duration=1, status_code="Active")


def test_activity_status_code_maps_only_supported_p6_wire_values() -> None:
    assert ActivityStatusCode.from_p6_value("What-If") is ActivityStatusCode.WHAT_IF


def test_activity_status_code_rejects_unknown_wire_values() -> None:
    with pytest.raises(ValueError, match="unsupported P6 Activity.StatusCode"):
        ActivityStatusCode.from_p6_value("Running")
