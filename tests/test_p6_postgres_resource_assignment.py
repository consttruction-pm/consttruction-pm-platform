from __future__ import annotations

import os
import uuid
from decimal import Decimal

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentPersistenceError,
    PostgresP6ResourceAssignmentRepository,
)


@pytest.fixture(scope="module")
def postgres_dsn() -> str:
    dsn = os.getenv("P6_TEST_POSTGRES_DSN") or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    if not dsn:
        pytest.skip("PostgreSQL DSN is not configured")
    return dsn


@pytest.fixture()
def connection(postgres_dsn):
    conn = psycopg.connect(postgres_dsn)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


def _scope() -> BackendScope:
    suffix = uuid.uuid4().hex
    return BackendScope(f"tenant-{suffix}", f"project-{suffix}", 7)


def _assignment(
    scope: BackendScope,
    calendar_version: str = "calendar-v3",
    is_driving: bool | None = None,
    assignment_id: str = "assignment-1",
    units_per_time: Decimal | None = None,
    units_per_time_period: str | None = None,
    hours_per_units_time_period: Decimal | None = None,
) -> P6ResourceAssignment:
    return P6ResourceAssignment(
        scope=scope,
        assignment_id=assignment_id,
        activity_id="activity-1",
        resource_id="resource-1",
        units=Decimal("8.50"),
        calendar_id="calendar-1",
        calendar_version=calendar_version,
        is_driving=is_driving,
        units_per_time=units_per_time,
        units_per_time_period=units_per_time_period,
        hours_per_units_time_period=hours_per_units_time_period,
    )


def test_postgres_resource_assignment_round_trips_exact_calendar_version(connection):
    repository = PostgresP6ResourceAssignmentRepository(connection)
    repository.initialize()
    scope = _scope()
    item = _assignment(scope)

    with connection.transaction():
        assert repository.upsert(item) == item
        assert repository.upsert(item) == item

    stored = repository.get(scope, item.assignment_id)
    assert stored == item
    assert stored.calendar_id == "calendar-1"
    assert stored.calendar_version == "calendar-v3"
    assert repository.list(scope) == (item,)


@pytest.mark.parametrize("is_driving", [True, False])
def test_postgres_resource_assignment_round_trips_driving_status(connection, is_driving):
    repository = PostgresP6ResourceAssignmentRepository(connection)
    repository.initialize()
    scope = _scope()
    item = _assignment(scope, is_driving=is_driving)

    with connection.transaction():
        assert repository.upsert(item) == item

    stored = repository.get(scope, item.assignment_id)
    assert stored is not None
    assert stored.is_driving is is_driving
    assert repository.list(scope) == (item,)


def test_postgres_resource_assignment_driving_status_is_immutable(connection):
    repository = PostgresP6ResourceAssignmentRepository(connection)
    repository.initialize()
    scope = _scope()
    original = _assignment(scope, is_driving=True)

    with connection.transaction():
        repository.upsert(original)

    with pytest.raises(
        P6ResourceAssignmentPersistenceError,
        match="IMMUTABLE_RESOURCE_ASSIGNMENT",
    ):
        repository.upsert(_assignment(scope, is_driving=False))


def test_postgres_legacy_assignment_table_migrates_without_guessing_version(connection):
    scope = _scope()
    # TEMP TABLE shadows the repository table for this connection, allowing an
    # isolated pre-migration schema test without mutating shared integration data.
    connection.execute(
        """CREATE TEMP TABLE p6_resource_assignment (
          tenant_id TEXT NOT NULL,
          project_id TEXT NOT NULL,
          project_revision BIGINT NOT NULL,
          assignment_id TEXT NOT NULL,
          activity_id TEXT NOT NULL,
          resource_id TEXT NOT NULL,
          role_id TEXT,
          units TEXT,
          actual_units TEXT,
          remaining_units TEXT,
          planned_cost TEXT,
          actual_cost TEXT,
          remaining_cost TEXT,
          unit TEXT,
          currency TEXT,
          calendar_id TEXT,
          note TEXT,
          PRIMARY KEY (tenant_id, project_id, assignment_id)
        ) ON COMMIT PRESERVE ROWS"""
    )
    connection.execute(
        "INSERT INTO p6_resource_assignment VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (scope.tenant_id, scope.project_id, scope.project_revision, "legacy-assignment",
         "activity-1", "resource-1", None, "8.5", None, None, None, None, None,
         "h", "USD", "calendar-1", "legacy row"),
    )

    repository = PostgresP6ResourceAssignmentRepository(connection)
    repository.initialize()
    legacy = repository.get(scope, "legacy-assignment")

    assert legacy is not None
    assert legacy.calendar_id == "calendar-1"
    # Migration preserves unknown provenance as NULL; it never guesses a version.
    assert legacy.calendar_version is None
    # New nullable fields must also remain unresolved for pre-existing rows.
    assert legacy.is_driving is None

    versioned = _assignment(scope, "calendar-v9")
    assert repository.upsert(versioned) == versioned
    assert repository.get(scope, versioned.assignment_id) == versioned


def test_postgres_resource_assignment_calendar_version_is_immutable(connection):
    repository = PostgresP6ResourceAssignmentRepository(connection)
    repository.initialize()
    scope = _scope()
    original = _assignment(scope, "calendar-v3")

    with connection.transaction():
        repository.upsert(original)

    with pytest.raises(
        P6ResourceAssignmentPersistenceError,
        match="IMMUTABLE_RESOURCE_ASSIGNMENT",
    ):
        repository.upsert(_assignment(scope, "calendar-v4"))



def test_postgres_resource_assignment_round_trips_assignment_units_per_time(connection):
    repository = PostgresP6ResourceAssignmentRepository(connection)
    repository.initialize()
    scope = _scope()
    item = _assignment(
        scope,
        units_per_time=Decimal("2.5"),
        units_per_time_period="day",
        hours_per_units_time_period=Decimal("8"),
    )

    with connection.transaction():
        assert repository.upsert(item) == item

    stored = repository.get(scope, item.assignment_id)
    assert stored == item
    assert stored.units_per_time == Decimal("2.5")
    assert stored.units_per_time_period == "day"
    assert stored.hours_per_units_time_period == Decimal("8")
