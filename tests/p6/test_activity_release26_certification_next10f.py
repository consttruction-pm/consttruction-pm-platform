from __future__ import annotations

import pytest

from construction_pm.p6_field_registry import P6FieldType, get_field


CASES = (
    ("AtCompletionLaborUnitsVariance", P6FieldType.DOUBLE, False, True, "units"),
    ("AtCompletionMaterialCost", P6FieldType.DOUBLE, False, True, "currency"),
    ("AtCompletionTotalCost", P6FieldType.DOUBLE, False, True, None),
    ("AtCompletionTotalUnits", P6FieldType.DOUBLE, False, True, None),
    ("DurationVariance", P6FieldType.DOUBLE, False, True, "working-time"),
    ("ExpenseCostPercentComplete", P6FieldType.DOUBLE, False, True, "percent"),
    ("ExpenseCostVariance", P6FieldType.DOUBLE, False, True, "currency"),
    ("LaborCost3Variance", P6FieldType.DOUBLE, False, True, "currency"),
    ("LaborCostPercentComplete", P6FieldType.DOUBLE, False, True, "percent"),
    ("LaborCostVariance", P6FieldType.DOUBLE, False, True, "currency"),
)


FIELD_IDS = {
    "AtCompletionLaborUnitsVariance": "activity.at_completion_labor_units_variance",
    "AtCompletionMaterialCost": "activity.at_completion_material_cost",
    "AtCompletionTotalCost": "activity.at_completion_total_cost",
    "AtCompletionTotalUnits": "activity.at_completion_total_units",
    "DurationVariance": "activity.duration_variance",
    "ExpenseCostPercentComplete": "activity.expense_cost_percent_complete",
    "ExpenseCostVariance": "activity.expense_cost_variance",
    "LaborCost3Variance": "activity.labor_cost3_variance",
    "LaborCostPercentComplete": "activity.labor_cost_percent_complete",
    "LaborCostVariance": "activity.labor_cost_variance",
}


@pytest.mark.parametrize(
    ("p6_field", "data_type", "writable", "computed", "unit"),
    CASES,
)
def test_activity_next10f_registry_metadata_is_deterministic(
    p6_field: str,
    data_type: P6FieldType,
    writable: bool,
    computed: bool,
    unit: str | None,
) -> None:
    field = get_field(FIELD_IDS[p6_field])
    assert field.p6_field == p6_field
    assert field.data_type is data_type
    assert field.writable is writable
    assert field.computed is computed
    assert field.unit == unit
    assert field.disposition == "seeded_not_certified"


def test_activity_next10f_has_no_duplicate_p6_identity() -> None:
    names = [p6_field for p6_field, *_ in CASES]
    assert len(names) == len(set(names))
