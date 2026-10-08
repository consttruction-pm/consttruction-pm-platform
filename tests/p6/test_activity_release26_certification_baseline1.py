from __future__ import annotations

import pytest

from construction_pm.p6_field_registry import P6FieldType, get_field


CASES = (
    ("Baseline1Duration", "activity.baseline1_duration", P6FieldType.DURATION, False, True, "working-time"),
    ("Baseline1FinishDate", "activity.baseline1_finish_date", P6FieldType.DATE, False, True, None),
    ("Baseline1PlannedDuration", "activity.baseline1_planned_duration", P6FieldType.DURATION, False, True, "working-time"),
    ("Baseline1PlannedExpenseCost", "activity.baseline1_planned_expense_cost", P6FieldType.DOUBLE, False, False, "currency"),
    ("Baseline1PlannedLaborCost", "activity.baseline1_planned_labor_cost", P6FieldType.DOUBLE, False, True, "currency"),
    ("Baseline1PlannedLaborUnits", "activity.baseline1_planned_labor_units", P6FieldType.DOUBLE, False, False, "units"),
    ("Baseline1PlannedMaterialCost", "activity.baseline1_planned_material_cost", P6FieldType.DOUBLE, False, False, "currency"),
    ("Baseline1PlannedNonLaborCost", "activity.baseline1_planned_non_labor_cost", P6FieldType.DOUBLE, False, True, "currency"),
    ("Baseline1PlannedNonLaborUnits", "activity.baseline1_planned_non_labor_units", P6FieldType.DOUBLE, False, False, "units"),
    ("Baseline1PlannedTotalCost", "activity.baseline1_planned_total_cost", P6FieldType.DOUBLE, False, True, "currency"),
    ("Baseline1StartDate", "activity.baseline1_start_date", P6FieldType.DATE, False, True, None),
)


@pytest.mark.parametrize(
    ("p6_field", "field_id", "data_type", "writable", "computed", "unit"),
    CASES,
)
def test_primary_baseline_registry_metadata_matches_certified_semantics(
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


def test_primary_baseline_certification_has_no_duplicate_p6_identities() -> None:
    names = [p6_field for p6_field, *_ in CASES]
    assert len(names) == len(set(names))
