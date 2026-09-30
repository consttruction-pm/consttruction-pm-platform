import os
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentPersistenceError,
    PostgresP6ResourceAssignmentRepository,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def connect():
    import psycopg
    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def assignment(scope, assignment_id="ra-1"):
    return P6ResourceAssignment(
        scope, assignment_id, "act-1", "res-1", "role-1",
        Decimal("8.5"), Decimal("2.5"), Decimal("6.0"),
        Decimal("850.25"), Decimal("250.00"), Decimal("600.25"),
        "h", "USD", "cal-1", "assignment snapshot",
    )


def test_postgres_round_trip_isolation_revision_and_decimal():
    with connect() as conn:
        repo = PostgresP6ResourceAssignmentRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-ra-pg", "project-ra-pg", 1)
        item = assignment(scope)
        assert repo.upsert(item) == item
        assert repo.get(scope, "ra-1") == item
        assert repo.get(BackendScope("other", "project-ra-pg", 1), "ra-1") is None
        assert repo.get(scope, "ra-1").units == Decimal("8.5")
        assert repo.get(scope, "ra-1").actual_cost == Decimal("250.00")
        with pytest.raises(P6ResourceAssignmentPersistenceError, match="REVISION_CONFLICT"):
            repo.get(BackendScope("tenant-ra-pg", "project-ra-pg", 2), "ra-1")


def test_postgres_immutable_replay_and_rollback():
    with connect() as conn:
        repo = PostgresP6ResourceAssignmentRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-ra-rb", "project-ra-rb", 1)
        item = assignment(scope)
        assert repo.upsert(item) == item
        assert repo.upsert(item) == item
        changed = P6ResourceAssignment(
            scope, "ra-1", "act-1", "res-1", "role-1",
            Decimal("9.5"), Decimal("2.5"), Decimal("7.0"),
            Decimal("950.25"), Decimal("250.00"), Decimal("700.25"),
            "h", "USD", "cal-1", "assignment snapshot",
        )
        with pytest.raises(P6ResourceAssignmentPersistenceError, match="IMMUTABLE_RESOURCE_ASSIGNMENT"):
            repo.upsert(changed)
        try:
            repo.upsert(assignment(scope, "rollback"))
            raise RuntimeError("force rollback")
        except RuntimeError:
            conn.rollback()
        assert repo.get(scope, "rollback") is None


from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignmentPeriodValue,
    PostgresP6ResourceAssignmentPeriodRepository,
)


def period_value(
    scope,
    period_start="2026-10-01",
    units="4.25",
    cost="425.50",
):
    return P6ResourceAssignmentPeriodValue(
        scope, "ra-period-1", "act-1", "res-1", period_start,
        Decimal(units), Decimal(cost),
    )


def test_postgres_assignment_period_round_trip_scope_revision_and_decimal():
    with connect() as conn:
        repo = PostgresP6ResourceAssignmentPeriodRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-period-pg", "project-period-pg", 1)
        first = period_value(scope)
        second = period_value(scope, "2026-10-02", "5.75", "575.00")
        assert repo.upsert(second) == second
        assert repo.upsert(first) == first
        assert repo.get(scope, "ra-period-1", "2026-10-01") == first
        assert [x.period_start for x in repo.list(scope, "ra-period-1")] == [
            "2026-10-01",
            "2026-10-02",
        ]
        assert repo.get(BackendScope("other-period", "project-period-pg", 1), "ra-period-1", "2026-10-01") is None
        with pytest.raises(P6ResourceAssignmentPersistenceError, match="REVISION_CONFLICT"):
            repo.get(BackendScope("tenant-period-pg", "project-period-pg", 2), "ra-period-1", "2026-10-01")


def test_postgres_assignment_period_identical_replay_and_immutable_conflict():
    with connect() as conn:
        repo = PostgresP6ResourceAssignmentPeriodRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-period-rb", "project-period-rb", 1)
        item = period_value(scope)
        assert repo.upsert(item) == item
        assert repo.upsert(item) == item
        changed = period_value(scope, units="4.50")
        with pytest.raises(
            P6ResourceAssignmentPersistenceError,
            match="IMMUTABLE_RESOURCE_ASSIGNMENT_PERIOD_VALUE",
        ):
            repo.upsert(changed)
