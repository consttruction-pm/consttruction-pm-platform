from __future__ import annotations

import pytest

from construction_pm.p6_field_registry import P6FieldType, get_field


CASES = (
    ("Baseline2Duration", "activity.baseline2_duration", P6FieldType.DOUBLE, False, True, "working-time"),
    ("Baseline2FinishDate", "activity.baseline2_finish_date", P6FieldType.DATE, False, True, None),
    ("Baseline2PlannedDuration", "activity.baseline2_planned_duration", P6FieldType.DOUBLE, False, True, "working-time"),
    ("Baseline2PlannedExpenseCost", "activity.baseline2_planned_expense_cost", P6FieldType.DOUBLE, False, True, "currency"),
    ("Baseline2PlannedLaborCost", "activity.baseline2_planned_labor_cost", P6FieldType.DOUBLE, False, True, "currency"),
    ("Baseline2PlannedLaborUnits", "activity.baseline2_planned_labor_units", P6FieldType.DOUBLE, False, True, "units"),
    ("Baseline2PlannedMaterialCost", "activity.baseline2_planned_material_cost", P6FieldType.DOUBLE, False, True, "currency"),
    ("Baseline2PlannedNonLaborCost", "activity.baseline2_planned_non_labor_cost", P6FieldType.DOUBLE, False, True, "currency"),
    ("Baseline2PlannedNonLaborUnits", "activity.baseline2_planned_non_labor_units", P6FieldType.DOUBLE, False, True, "units"),
    ("Baseline2PlannedTotalCost", "activity.baseline2_planned_total_cost", P6FieldType.DOUBLE, False, True, "currency"),
    ("Baseline2StartDate", "activity.baseline2_start_date", P6FieldType.DATE, False, True, None),
)


@pytest.mark.parametrize(
    ("p6_field", "field_id", "data_type", "writable", "computed", "unit"),
    CASES,
)
def test_secondary_baseline_registry_metadata_matches_release26_certification(
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
    assert field.read_only is True
    assert field.disposition == "seeded_not_certified"


def test_secondary_baseline_certification_has_no_duplicate_p6_identities() -> None:
    names = [p6_field for p6_field, *_ in CASES]
    assert len(names) == len(set(names))
