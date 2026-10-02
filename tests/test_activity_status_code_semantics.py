from construction_pm.scheduling.activity import Activity, ActivityStatusCode
import pytest


def test_activity_status_code_matches_p6_semantic_values() -> None:
    assert [item.value for item in ActivityStatusCode] == [
        "Planned",
        "Active",
        "Inactive",
        "What-If",
        "Requested",
        "Template",
    ]


def test_activity_status_code_is_an_explicit_typed_enum() -> None:
    with pytest.raises(TypeError, match="status_code"):
        Activity(id="A-1", duration=1, status_code="Active")
