from construction_pm.p6_activity_type_evidence import (
    activity_exact_type_evidence,
    get_activity_type_evidence,
)
from construction_pm.p6_field_registry import fields_by_subject


def test_exact_activity_registry_fields_have_release_26_wire_type_evidence():
    registry_fields = {
        field.p6_field for field in fields_by_subject("Activity")
    }
    evidence_fields = {
        evidence.p6_field for evidence in activity_exact_type_evidence()
    }

    assert len(evidence_fields) == 30
    assert registry_fields & evidence_fields == evidence_fields


def test_activity_type_evidence_keeps_api_wire_type_distinct_from_canonical_type():
    assert get_activity_type_evidence("PlannedDuration").source_wire_type == "double"
    assert get_activity_type_evidence("PlannedStartDate").source_wire_type == "date-time"
    assert get_activity_type_evidence("FloatPath").source_wire_type == "integer"
    assert get_activity_type_evidence("PercentCompleteType").source_wire_type == "string"


def test_activity_type_evidence_is_not_field_certification():
    assert all(
        evidence.status == "type_verified_not_certified"
        for evidence in activity_exact_type_evidence()
    )
    assert get_activity_type_evidence("CreateUser").source_url.startswith(
        "https://docs.oracle.com/"
    )
