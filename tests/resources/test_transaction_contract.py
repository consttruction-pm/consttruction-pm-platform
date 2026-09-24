import sqlite3
from decimal import Decimal

from construction_pm.resources.models import ResourceAssignment
from construction_pm.resources.persistence import SQLiteResourceRepository


def test_nested_transaction_participates_in_outer_atomic_boundary():
    repo = SQLiteResourceRepository(sqlite3.connect(":memory:"))
    resource = repo.get_resource("missing")
    assert resource is None

    with repo.transaction():
        repo.save_resource(
            __import__("tests.resources.test_persistence", fromlist=["make_resource"]).make_resource()
        )
        with repo.transaction():
            repo.save_assignment(
                ResourceAssignment(
                    activity_id="a1",
                    resource_id="r1",
                    planned_units=Decimal("2"),
                )
            )

    assert repo.get_resource("r1") is not None
    assert repo.list_assignments("a1")


def test_nested_transaction_failure_rolls_back_outer_work():
    repo = SQLiteResourceRepository(sqlite3.connect(":memory:"))

    try:
        with repo.transaction():
            repo.save_resource(
                __import__("tests.resources.test_persistence", fromlist=["make_resource"]).make_resource()
            )
            with repo.transaction():
                raise RuntimeError("abort")
    except RuntimeError:
        pass

    assert repo.get_resource("r1") is None
    assert repo.list_assignments() == []
