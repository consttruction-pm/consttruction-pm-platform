from decimal import Decimal
from construction_pm.resources.models import ResourceAssignment
from construction_pm.resources.xlsx_io import export_resources_xlsx, import_assignment_rows_xlsx

def test_xlsx_assignment_round_trip_preserves_numeric_types():
    assignment = ResourceAssignment(
        activity_id="A-1", resource_id="R-1",
        planned_units=Decimal("10.50"), actual_units=Decimal("4.25"),
        remaining_units=Decimal("6.25"), planned_cost=Decimal("1000.00"),
        actual_cost=Decimal("425.00"), remaining_cost=Decimal("575.00"),
    )
    data = export_resources_xlsx([], [assignment])
    rows = import_assignment_rows_xlsx(data)
    assert rows[0]["planned_units"] == Decimal("10.50")
    assert rows[0]["actual_cost"] == Decimal("425.00")
