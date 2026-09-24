import sqlite3
from decimal import Decimal

from construction_pm.resources.models import Resource, ResourceAssignment, ResourceType
from construction_pm.resources.persistence import SQLiteResourceRepository


def make_resource() -> Resource:
    return Resource(id="r1", code="LAB-01", name="Crew", resource_type=ResourceType.LABOR, unit="hour")


def test_nested_transaction_participates_in_outer_atomic_boundary():
    repo = SQLiteResourceRepository(sqlite3.connect(":memory:"))

    with repo.transaction():
        repo.save_resource(make_resource())
        with repo.transaction():
            repo.save_assignment(
                ResourceAssignment(activity_id="a1", resource_id="r1", planned_units=Decimal("2"))
            )

    assert repo.get_resource("r1") is not None
    assert repo.list_assignments("a1")


def test_nested_transaction_failure_rolls_back_outer_work():
    repo = SQLiteResourceRepository(sqlite3.connect(":memory:"))

    try:
        with repo.transaction():
            repo.save_resource(make_resource())
            with repo.transaction():
                raise RuntimeError("abort")
    except RuntimeError:
        pass

    assert repo.get_resource("r1") is None
    assert repo.list_assignments() == []
