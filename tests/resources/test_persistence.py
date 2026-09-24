import sqlite3
from datetime import date
from decimal import Decimal

from construction_pm.resources.models import CostBasis, Resource, ResourceAssignment, ResourceRate, ResourceType
from construction_pm.resources.persistence import SQLiteResourceRepository


def test_sqlite_resource_and_assignment_round_trip():
    repo = SQLiteResourceRepository(sqlite3.connect(":memory:"))
    resource = Resource(
        id="R-1", code="LAB-01", name="Labor",
        resource_type=ResourceType.LABOR, unit="hour",
        rates=[ResourceRate(
            rate=Decimal("25.50"), basis=CostBasis.PER_HOUR, currency="USD",
            effective_from=date(2026, 1, 1), version=2,
        )],
    )
    repo.save_resource(resource)
    assignment = ResourceAssignment(
        activity_id="A-1", resource_id="R-1",
        planned_units=Decimal("10.50"), actual_units=Decimal("4.25"),
        remaining_units=Decimal("6.25"), planned_cost=Decimal("1000.00"),
        actual_cost=Decimal("425.00"), remaining_cost=Decimal("575.00"),
    )
    repo.save_assignment(assignment)
    assert repo.get_resource("R-1") == resource
    assert repo.list_assignments("A-1") == [assignment]


def test_sqlite_foreign_key_rejects_unknown_resource():
    repo = SQLiteResourceRepository(sqlite3.connect(":memory:"))
    assignment = ResourceAssignment(
        activity_id="A-1", resource_id="R-X",
        planned_units=Decimal("1"), actual_units=Decimal("0"),
    )
    import pytest
    with pytest.raises(Exception):
        repo.save_assignment(assignment)


def test_sqlite_decimal_values_are_stored_as_exact_text():
    repo = SQLiteResourceRepository(sqlite3.connect(":memory:"))
    resource = Resource(
        id="R-1", code="LAB-01", name="Labor",
        resource_type=ResourceType.LABOR, unit="hour",
    )
    repo.save_resource(resource)
    repo.save_assignment(ResourceAssignment(
        activity_id="A-1", resource_id="R-1",
        planned_units=Decimal("0.10"), actual_units=Decimal("0.03"),
    ))
    row = repo.connection.execute(
        "SELECT planned_units, actual_units FROM resource_assignments"
    ).fetchone()
    assert row == ("0.10", "0.03")
