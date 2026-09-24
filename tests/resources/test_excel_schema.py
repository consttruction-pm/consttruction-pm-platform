from datetime import date
from decimal import Decimal
import pytest
from construction_pm.resources.excel_schema import ASSIGNMENT_COLUMNS, coerce_excel_value

def test_assignment_cost_and_units_are_numeric_columns():
    fields = {c.field: c.data_type for c in ASSIGNMENT_COLUMNS}
    assert fields["planned_units"] == "number"
    assert fields["actual_cost"] == "number"
    assert fields["remaining_cost"] == "number"

def test_numeric_excel_values_become_decimal():
    assert coerce_excel_value(12.5, "number") == Decimal("12.5")

def test_date_is_typed():
    assert coerce_excel_value("2026-09-24", "date") == date(2026, 9, 24)

def test_boolean_rejects_unknown_value():
    with pytest.raises(ValueError):
        coerce_excel_value("maybe", "boolean")
