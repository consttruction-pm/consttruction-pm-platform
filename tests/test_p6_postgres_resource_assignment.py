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


def _assignment(scope: BackendScope, calendar_version: str = "calendar-v3") -> P6ResourceAssignment:
    return P6ResourceAssignment(
        scope=scope,
        assignment_id="assignment-1",
        activity_id="activity-1",
        resource_id="resource-1",
        units=Decimal("8.50"),
        calendar_id="calendar-1",
        calendar_version=calendar_version,
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
