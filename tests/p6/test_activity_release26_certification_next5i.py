from __future__ import annotations

import pytest

from construction_pm.p6_field_registry import P6FieldType, get_field


CASES = (
    ("BaselineStartDate", "activity.baseline_start", P6FieldType.DATE, False, True, None),
    ("BaselineFinishDate", "activity.baseline_finish", P6FieldType.DATE, False, True, None),
    ("BaselineDuration", "activity.baseline_duration", P6FieldType.DURATION, False, True, "working-time"),
    ("PrimaryConstraintDate", "activity.primary_constraint_date", P6FieldType.DATE, True, False, None),
    ("ExpectedFinishDate", "activity.expected_finish", P6FieldType.DATE, True, False, None),
)


@pytest.mark.parametrize(
    ("p6_field", "field_id", "data_type", "writable", "computed", "unit"),
    CASES,
)
def test_activity_next5i_registry_metadata_is_deterministic(
    p6_field: str, field_id: str, data_type: P6FieldType,
    writable: bool, computed: bool, unit: str | None,
) -> None:
    field = get_field(field_id)
    assert field.p6_field == p6_field
    assert field.data_type is data_type
    assert field.writable is writable
    assert field.computed is computed
    assert field.unit == unit
    assert field.disposition == "seeded_not_certified"


def test_activity_next5i_has_no_duplicate_p6_identity() -> None:
    names = [p6_field for p6_field, *_ in CASES]
    assert len(names) == len(set(names))
