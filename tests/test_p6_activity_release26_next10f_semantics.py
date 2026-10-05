from __future__ import annotations

import pytest

from construction_pm.p6_field_registry import P6FieldType, get_field


CASES = (
    ("AtCompletionDuration", "activity.at_completion_duration", P6FieldType.DOUBLE, False, True, "working-time"),
    ("CostPercentComplete", "activity.cost_percent_complete", P6FieldType.DOUBLE, False, True, "percent"),
    ("CostPercentOfPlanned", "activity.cost_percent_of_planned", P6FieldType.DOUBLE, False, True, "percent"),
    ("CostPerformanceIndex", "activity.cost_performance_index", P6FieldType.DOUBLE, False, True, None),
    ("Duration1Variance", "activity.duration1_variance", P6FieldType.DOUBLE, False, True, "working-time"),
    ("DurationVariance", "activity.duration_variance", P6FieldType.DOUBLE, False, True, "working-time"),
    ("ExpenseCostPercentComplete", "activity.expense_cost_percent_complete", P6FieldType.DOUBLE, False, True, "percent"),
    ("ExpenseCostVariance", "activity.expense_cost_variance", P6FieldType.DOUBLE, False, True, "currency"),
    ("ActualExpenseCost", "activity.actual_expense_cost", P6FieldType.DOUBLE, False, True, None),
    ("ActualMaterialCost", "activity.actual_material_cost", P6FieldType.DOUBLE, False, True, None),
)


@pytest.mark.parametrize(
    ("p6_field", "field_id", "data_type", "writable", "computed", "unit"),
    CASES,
)
def test_activity_next10f_registry_metadata_is_deterministic(
    p6_field: str,
    field_id: str,
    data_type: P6FieldType,
    writable: bool,
    computed: bool,
    unit: str | None,
) -> None:
    field = get_field(field_id)
    assert field is not None
    assert field.p6_field == p6_field
    assert field.data_type is data_type
    assert field.writable is writable
    assert field.computed is computed
    assert field.unit == unit
    assert field.disposition == "seeded_not_certified"


def test_activity_next10f_has_no_duplicate_p6_identity() -> None:
    p6_names = [get_field(field_id).p6_field for _, field_id, *_ in CASES]
    assert len(p6_names) == len(set(p6_names))
