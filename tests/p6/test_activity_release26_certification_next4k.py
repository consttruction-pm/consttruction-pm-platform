from __future__ import annotations

import pytest

from construction_pm.p6_field_registry import P6FieldType, get_field


CASES = (
    ("AutoComputeActuals", "activity.auto_compute_actuals", P6FieldType.BOOLEAN, True, False, None),
    ("ActualTotalUnits", "activity.actual_total_units", P6FieldType.DOUBLE, False, True, None),
    ("AtCompletionTotalCost", "activity.at_completion_total_cost", P6FieldType.DOUBLE, False, True, None),
    ("AtCompletionTotalUnits", "activity.at_completion_total_units", P6FieldType.DOUBLE, False, True, None),
)


@pytest.mark.parametrize(
    ("p6_field", "field_id", "data_type", "writable", "computed", "unit"),
    CASES,
)
def test_activity_next4k_registry_metadata_matches_certified_semantics(
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


def test_activity_next4k_has_no_duplicate_p6_identity() -> None:
    names = [p6_field for p6_field, *_ in CASES]
    assert len(names) == len(set(names))
