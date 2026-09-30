import sqlite3
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentPersistenceError,
    SQLiteP6ResourceAssignmentRepository,
)


def scope(revision=1):
    return BackendScope("tenant-a", "project-a", revision)


def assignment(s, assignment_id="ra-1", activity_id="act-1", resource_id="res-1"):
    return P6ResourceAssignment(
        s, assignment_id, activity_id, resource_id, "role-1",
        Decimal("8.5"), Decimal("2.5"), Decimal("6.0"),
        Decimal("850.25"), Decimal("250.00"), Decimal("600.25"),
        "h", "USD", "cal-1", "assignment snapshot",
    )


def test_round_trip_and_deterministic_list():
    repo = SQLiteP6ResourceAssignmentRepository(sqlite3.connect(":memory:"))
    repo.upsert(assignment(scope(), "b"))
    repo.upsert(assignment(scope(), "a"))
    assert repo.get(scope(), "a") == assignment(scope(), "a")
    assert [x.assignment_id for x in repo.list(scope())] == ["a", "b"]
    assert [x.assignment_id for x in repo.list(scope(), activity_id="act-1")] == ["a", "b"]
    assert [x.assignment_id for x in repo.list(scope(), resource_id="res-1")] == ["a", "b"]


def test_scope_isolation_and_revision_conflict():
    repo = SQLiteP6ResourceAssignmentRepository(sqlite3.connect(":memory:"))
    repo.upsert(assignment(scope()))
    assert repo.get(BackendScope("tenant-b", "project-a", 1), "ra-1") is None
    assert repo.get(BackendScope("tenant-a", "project-b", 1), "ra-1") is None
    with pytest.raises(P6ResourceAssignmentPersistenceError, match="REVISION_CONFLICT"):
        repo.get(scope(2), "ra-1")
    with pytest.raises(P6ResourceAssignmentPersistenceError, match="REVISION_CONFLICT"):
        repo.upsert(assignment(scope(2)))


def test_definition_is_immutable_but_identical_replay_is_idempotent():
    repo = SQLiteP6ResourceAssignmentRepository(sqlite3.connect(":memory:"))
    item = assignment(scope())
    assert repo.upsert(item) == item
    assert repo.upsert(item) == item
    changed = P6ResourceAssignment(
        scope(), "ra-1", "act-1", "res-1", "role-1",
        Decimal("9.5"), Decimal("2.5"), Decimal("7.0"),
        Decimal("950.25"), Decimal("250.00"), Decimal("700.25"),
        "h", "USD", "cal-1", "assignment snapshot",
    )
    with pytest.raises(P6ResourceAssignmentPersistenceError, match="IMMUTABLE_RESOURCE_ASSIGNMENT"):
        repo.upsert(changed)


def test_typed_decimal_and_invalid_values_fail_closed():
    item = assignment(scope())
    assert item.units == Decimal("8.5")
    assert item.actual_cost == Decimal("250.00")
    with pytest.raises(P6ResourceAssignmentPersistenceError, match="INVALID_UNITS"):
        P6ResourceAssignment(scope(), "ra-1", "act-1", "res-1", units=Decimal("NaN")).validate()
    with pytest.raises(P6ResourceAssignmentPersistenceError, match="INVALID_RESOURCE_ID"):
        P6ResourceAssignment(scope(), "ra-1", "act-1", " ").validate()
    with pytest.raises(P6ResourceAssignmentPersistenceError, match="INVALID_CURRENCY"):
        P6ResourceAssignment(scope(), "ra-1", "act-1", "res-1", currency="").validate()


from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignmentPeriodValue,
    SQLiteP6ResourceAssignmentPeriodRepository,
)


def period_value(
    revision=1,
    assignment_id="ra-1",
    period_start="2026-10-01",
    units="4.25",
    cost="425.50",
):
    return P6ResourceAssignmentPeriodValue(
        scope(revision),
        assignment_id,
        "act-1",
        "res-1",
        period_start,
        Decimal(units),
        Decimal(cost),
    )


def test_assignment_period_round_trip_and_deterministic_ordering():
    repo = SQLiteP6ResourceAssignmentPeriodRepository(sqlite3.connect(":memory:"))
    later = period_value(period_start="2026-10-02")
    first = period_value(period_start="2026-10-01")
    assert repo.upsert(later) == later
    assert repo.upsert(first) == first
    assert repo.get(scope(), "ra-1", "2026-10-01") == first
    assert [x.period_start for x in repo.list(scope(), "ra-1")] == [
        "2026-10-01",
        "2026-10-02",
    ]


def test_assignment_period_scope_revision_and_immutability():
    repo = SQLiteP6ResourceAssignmentPeriodRepository(sqlite3.connect(":memory:"))
    item = period_value()
    assert repo.upsert(item) == item
    assert repo.upsert(item) == item
    assert repo.get(BackendScope("tenant-b", "project-a", 1), "ra-1", "2026-10-01") is None
    with pytest.raises(P6ResourceAssignmentPersistenceError, match="REVISION_CONFLICT"):
        repo.get(scope(2), "ra-1", "2026-10-01")
    changed = period_value(units="5.25")
    with pytest.raises(
        P6ResourceAssignmentPersistenceError,
        match="IMMUTABLE_RESOURCE_ASSIGNMENT_PERIOD_VALUE",
    ):
        repo.upsert(changed)


def test_assignment_period_decimal_validation_fails_closed():
    item = period_value()
    assert item.units == Decimal("4.25")
    assert item.cost == Decimal("425.50")
    with pytest.raises(P6ResourceAssignmentPersistenceError, match="INVALID_UNITS"):
        period_value(units="NaN").validate()
    with pytest.raises(P6ResourceAssignmentPersistenceError, match="INVALID_PERIOD_START"):
        period_value(period_start="").validate()
