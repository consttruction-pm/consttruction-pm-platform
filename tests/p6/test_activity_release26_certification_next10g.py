from __future__ import annotations

import pytest

from construction_pm.p6_field_registry import P6FieldType, get_field


CASES = (
    ("PlannedStartDate", "activity.planned_start", P6FieldType.DATE, True, False, None),
    ("PlannedFinishDate", "activity.planned_finish", P6FieldType.DATE, True, False, None),
    ("ActualStartDate", "activity.actual_start", P6FieldType.DATE, True, False, None),
    ("ActualFinishDate", "activity.actual_finish", P6FieldType.DATE, True, False, None),
    ("RemainingDuration", "activity.remaining_duration", P6FieldType.DURATION, False, True, "working-time"),
    ("ActualDuration", "activity.actual_duration", P6FieldType.DURATION, False, True, "working-time"),
    ("DurationPercentComplete", "activity.duration_percent_complete", P6FieldType.PERCENTAGE, False, True, "percent"),
    ("PhysicalPercentComplete", "activity.physical_percent_complete", P6FieldType.PERCENTAGE, True, False, "percent"),
    ("PercentCompleteType", "activity.percent_complete_type", P6FieldType.ENUM, True, False, None),
    ("TotalFloat", "activity.total_float", P6FieldType.DURATION, False, True, "working-time"),
)


@pytest.mark.parametrize(
    ("p6_field", "field_id", "data_type", "writable", "computed", "unit"),
    CASES,
)
def test_activity_next10g_registry_metadata_is_deterministic(
    p6_field: str,
    field_id: str,
    data_type: P6FieldType,
    writable: bool,
    computed: bool,
    unit: str | None,
) -> None:
    field = get_field(field_id)
    assert field.p6_field == p6_field
    assert field.data_type is data_type
    assert field.writable is writable
    assert field.computed is computed
    assert field.unit == unit
    assert field.disposition == "seeded_not_certified"


def test_activity_next10g_has_no_duplicate_p6_identity() -> None:
    names = [p6_field for p6_field, *_ in CASES]
    assert len(names) == len(set(names))
