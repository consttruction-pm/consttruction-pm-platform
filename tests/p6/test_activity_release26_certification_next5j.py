from __future__ import annotations

import pytest

from construction_pm.p6_field_registry import P6FieldType, get_field


CASES = (
    ("SuspendDate", "activity.suspend_date", P6FieldType.DATETIME, True, False, None),
    ("TaskStatusCompletion", "activity.task_status_completion", P6FieldType.COMPLEX, True, False, None),
    ("TaskStatusDates", "activity.task_status_dates", P6FieldType.COMPLEX, True, False, None),
    ("TaskStatusIndicator", "activity.task_status_indicator", P6FieldType.BOOLEAN, True, False, None),
    ("UnitsPercentComplete", "activity.units_percent_complete", P6FieldType.DOUBLE, False, True, "percent"),
)


@pytest.mark.parametrize(
    ("p6_field", "field_id", "data_type", "writable", "computed", "unit"),
    CASES,
)
def test_activity_next5j_registry_metadata_matches_oracle_evidence(
    p6_field: str,
    field_id: str,
    data_type: P6FieldType,
    writable: bool,
    computed: bool,
    unit: str | None,
) -> None:
    field = get_field(field_id)
    assert field.subject_area == "Activity"
    assert field.p6_field == p6_field
    assert field.data_type is data_type
    assert field.writable is writable
    assert field.computed is computed
    assert field.unit == unit
    assert field.disposition == "seeded_not_certified"


def test_activity_next5j_has_no_duplicate_p6_identity() -> None:
    names = [p6_field for p6_field, *_ in CASES]
    assert len(names) == len(set(names))
