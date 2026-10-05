from __future__ import annotations

import pytest

from construction_pm.p6_field_registry import P6FieldType, get_field


CASES = (
    ("AtCompletionLaborCost", "activity.at_completion_labor_cost", P6FieldType.DOUBLE, False, True, "currency"),
    ("AtCompletionLaborUnits", "activity.at_completion_labor_units", P6FieldType.DOUBLE, False, True, "units"),
    ("AtCompletionMaterialCost", "activity.at_completion_material_cost", P6FieldType.DOUBLE, False, True, "currency"),
    ("AtCompletionNonLaborCost", "activity.at_completion_non_labor_cost", P6FieldType.DOUBLE, False, True, "currency"),
    ("AtCompletionNonLaborUnits", "activity.at_completion_non_labor_units", P6FieldType.DOUBLE, False, True, "units"),
)


@pytest.mark.parametrize(
    ("p6_field", "field_id", "data_type", "writable", "computed", "unit"),
    CASES,
)
def test_activity_next5l_registry_metadata_matches_certified_semantics(
    p6_field: str,
    field_id: str,
    data_type: P6FieldType,
    writable: bool,
    computed: bool,
    unit: str,
) -> None:
    field = get_field(field_id)
    assert field.p6_field == p6_field
    assert field.subject_area == "Activity"
    assert field.data_type is data_type
    assert field.writable is writable
    assert field.computed is computed
    assert field.unit == unit
    assert field.disposition == "seeded_not_certified"


def test_activity_next5l_has_no_duplicate_p6_identity() -> None:
    names = [p6_field for p6_field, *_ in CASES]
    assert len(names) == len(set(names))
