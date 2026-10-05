from __future__ import annotations

import pytest

from construction_pm.p6_field_registry import P6FieldType, get_field


CASES = (
    ("ActualExpenseCost", "activity.actual_expense_cost", P6FieldType.DOUBLE, False, True, None),
    ("ActualMaterialCost", "activity.actual_material_cost", P6FieldType.DOUBLE, False, True, None),
    ("ActualNonLaborCost", "activity.actual_non_labor_cost", P6FieldType.DOUBLE, True, False, None),
    ("ActualNonLaborUnits", "activity.actual_non_labor_units", P6FieldType.DOUBLE, True, False, None),
    ("ActualThisPeriodLaborCost", "activity.actual_this_period_labor_cost", P6FieldType.DOUBLE, True, False, None),
    ("ActualThisPeriodLaborUnits", "activity.actual_this_period_labor_units", P6FieldType.DOUBLE, True, False, None),
    ("ActualThisPeriodMaterialCost", "activity.actual_this_period_material_cost", P6FieldType.DOUBLE, False, True, None),
    ("ActualThisPeriodNonLaborCost", "activity.actual_this_period_non_labor_cost", P6FieldType.DOUBLE, True, False, None),
    ("ActualThisPeriodNonLaborUnits", "activity.actual_this_period_non_labor_units", P6FieldType.DOUBLE, True, False, None),
    ("ActualTotalCost", "activity.actual_total_cost", P6FieldType.DOUBLE, False, True, None),
)


@pytest.mark.parametrize(
    ("p6_field", "field_id", "data_type", "writable", "computed", "unit"),
    CASES,
)
def test_activity_next10h_registry_metadata_matches_certified_disposition(
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


def test_activity_next10h_has_no_duplicate_p6_identity() -> None:
    names = [p6_field for p6_field, *_ in CASES]
    assert len(names) == len(set(names))
