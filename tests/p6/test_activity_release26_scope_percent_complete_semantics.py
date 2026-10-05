from __future__ import annotations

from construction_pm.p6_field_registry import P6FieldType, get_field


def test_scope_percent_complete_matches_release26_semantics() -> None:
    field = get_field("activity.scope_percent_complete")
    assert field.subject_area == "Activity"
    assert field.p6_field == "ScopePercentComplete"
    assert field.data_type is P6FieldType.DOUBLE
    assert field.writable is True
    assert field.computed is False
    assert field.unit == "percent"
    assert field.disposition == "seeded_not_certified"


def test_scope_percent_complete_identity_is_unique() -> None:
    matches = [
        field
        for field in (get_field("activity.scope_percent_complete"),)
        if field.p6_field == "ScopePercentComplete"
    ]
    assert len(matches) == 1
