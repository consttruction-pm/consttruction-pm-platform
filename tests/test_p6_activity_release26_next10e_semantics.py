from __future__ import annotations

import pytest

from construction_pm.p6_field_registry import P6FieldType, get_field


CASES = (
    ("AccountingVariance", P6FieldType.DOUBLE, False, True, None),
    ("AccountingVarianceLaborUnits", P6FieldType.DOUBLE, False, True, None),
    ("AtCompletionVariance", P6FieldType.DOUBLE, False, True, "currency"),
    ("Duration2Variance", P6FieldType.DOUBLE, False, True, "working-time"),
    ("Duration3Variance", P6FieldType.DOUBLE, False, True, "working-time"),
    ("DurationPercentOfPlanned", P6FieldType.DOUBLE, False, True, "percent"),
    ("EarnedValueCost", P6FieldType.DOUBLE, False, True, "currency"),
    ("ExpenseCost1Variance", P6FieldType.DOUBLE, False, True, "currency"),
    ("ExpenseCost2Variance", P6FieldType.DOUBLE, False, True, "currency"),
    ("ExpenseCost3Variance", P6FieldType.DOUBLE, False, True, "currency"),
)


@pytest.mark.parametrize(
    ("p6_field", "data_type", "writable", "computed", "unit"),
    CASES,
)
def test_activity_next10e_registry_metadata_is_deterministic(
    p6_field: str,
    data_type: P6FieldType,
    writable: bool,
    computed: bool,
    unit: str | None,
) -> None:
    matches = [
        field
        for field in (
            get_field("activity.accounting_variance"),
            get_field("activity.accounting_variance_labor_units"),
            get_field("activity.at_completion_variance"),
            get_field("activity.duration2_variance"),
            get_field("activity.duration3_variance"),
            get_field("activity.duration_percent_of_planned"),
            get_field("activity.earned_value_cost"),
            get_field("activity.expense_cost1_variance"),
            get_field("activity.expense_cost2_variance"),
            get_field("activity.expense_cost3_variance"),
        )
        if field.p6_field == p6_field
    ]
    assert len(matches) == 1

    field = matches[0]
    assert field.data_type is data_type
    assert field.writable is writable
    assert field.computed is computed
    assert field.unit == unit
    assert field.disposition == "seeded_not_certified"


def test_activity_next10e_has_no_duplicate_p6_identity() -> None:
    p6_names = [get_field(field_id).p6_field for field_id, *_ in (
        ("activity.accounting_variance",),
        ("activity.accounting_variance_labor_units",),
        ("activity.at_completion_variance",),
        ("activity.duration2_variance",),
        ("activity.duration3_variance",),
        ("activity.duration_percent_of_planned",),
        ("activity.earned_value_cost",),
        ("activity.expense_cost1_variance",),
        ("activity.expense_cost2_variance",),
        ("activity.expense_cost3_variance",),
    )]
    assert len(p6_names) == len(set(p6_names))
