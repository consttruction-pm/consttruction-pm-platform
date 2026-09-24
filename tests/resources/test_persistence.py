import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from construction_pm.resources.models import CostBasis, Resource, ResourceAssignment, ResourceRate, ResourceType
from construction_pm.resources.persistence import OptimisticLockError, SQLiteResourceRepository


def make_resource(resource_id: str = "r1") -> Resource:
    return Resource(
        id=resource_id, code="LAB-01", name="Crew", resource_type=ResourceType.LABOR, unit="hour",
        rates=[ResourceRate(rate=Decimal("125.50"), basis=CostBasis.PER_HOUR, currency="USD",
                            effective_from=date(2026, 1, 1), version=2)],
    )


def test_resource_and_assignment_round_trip() -> None:
    repo = SQLiteResourceRepository(sqlite3.connect(":memory:"))
    resource = make_resource()
    assignment = ResourceAssignment(activity_id="a1", resource_id="r1", planned_units=Decimal("10.25"),
                                    actual_units=Decimal("4.25"), remaining_units=Decimal("6.00"),
                                    planned_cost=Decimal("1286.375"))
    with repo.transaction():
        repo.save_resource(resource)
        repo.save_assignment(assignment)
    assert repo.get_resource("r1") == resource
    assert repo.list_assignments("a1") == [assignment]


def test_transaction_rolls_back_resource_and_assignment_together() -> None:
    repo = SQLiteResourceRepository(sqlite3.connect(":memory:"))
    with pytest.raises(sqlite3.IntegrityError):
        with repo.transaction():
            repo.save_resource(make_resource())
            repo.save_assignment(ResourceAssignment(activity_id="a1", resource_id="missing", planned_units=Decimal("1")))
    assert repo.get_resource("r1") is None
    assert repo.list_assignments() == []


def test_decimal_values_are_stored_as_exact_text() -> None:
    connection = sqlite3.connect(":memory:")
    repo = SQLiteResourceRepository(connection)
    repo.save_resource(make_resource())
    repo.save_assignment(ResourceAssignment(activity_id="a1", resource_id="r1",
                                            planned_units=Decimal("10.2500"), actual_units=Decimal("4.2500")))
    assert connection.execute("SELECT planned_units, actual_units FROM resource_assignments").fetchone() == ("10.2500", "4.2500")


def test_versioned_resource_rate_round_trip() -> None:
    repo = SQLiteResourceRepository(sqlite3.connect(":memory:"))
    resource = Resource(id="r2", code="MAT-01", name="Concrete", resource_type=ResourceType.MATERIAL, unit="m3",
                        rates=[ResourceRate(rate=Decimal("99.95"), basis=CostBasis.PER_UNIT, currency="EUR",
                                            effective_from=date(2026, 2, 1), effective_to=date(2026, 12, 31), version=7)])
    repo.save_resource(resource)
    assert repo.get_resource("r2") == resource


def test_optimistic_revision_rejects_stale_update() -> None:
    repo = SQLiteResourceRepository(sqlite3.connect(":memory:"))
    resource = make_resource()
    repo.save_resource(resource)
    revision = repo.get_resource_revision("r1")
    assert revision == 1
    updated = Resource(id=resource.id, code=resource.code, name="Crew Updated",
                       resource_type=resource.resource_type, unit=resource.unit, rates=resource.rates,
                       calendar_id=resource.calendar_id, active=resource.active)
    repo.save_resource(updated, expected_revision=revision)
    assert repo.get_resource_revision("r1") == 2
    with pytest.raises(OptimisticLockError):
        repo.save_resource(resource, expected_revision=revision)


def test_transaction_configuration_is_explicit_and_rollback_safe() -> None:
    repo = SQLiteResourceRepository(sqlite3.connect(":memory:"))
    with pytest.raises(RuntimeError):
        with repo.transaction():
            repo.save_resource(make_resource())
            raise RuntimeError("abort")
    assert repo.get_resource("r1") is None
