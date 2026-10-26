from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_capacity_repository import (
    P6ResourceCapacityRecord,
    PostgresP6ResourceCapacityRepository,
)
from construction_pm.resources.max_units_time import (
    ResourceCapacityBasis,
    ResourceMaxUnitsTime,
    ResourceMaxUnitsTimeProfile,
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
    return BackendScope(f"tenant-{suffix}", f"project-{suffix}", 3)


def _segment(
    *,
    resource_id: str = "CREW-1",
    max_units: str = "8",
    start: date = date(2026, 10, 1),
    end: date | None = None,
    source: str = "manual-entry",
) -> ResourceMaxUnitsTime:
    return ResourceMaxUnitsTime.create(
        resource_id=resource_id,
        max_units=Decimal(max_units),
        unit_basis=ResourceCapacityBasis.DAY,
        hours_per_time_period=Decimal("8"),
        effective_from=start,
        effective_to=end,
        source=source,
    )


def test_postgres_effective_change_is_append_only_and_idempotent(connection):
    repository = PostgresP6ResourceCapacityRepository(connection)
    repository.initialize()
    scope = _scope()
    original = _segment()
    replacement = _segment(max_units="10", start=date(2026, 11, 1))

    with connection.transaction():
        repository.save_effective_change(
            P6ResourceCapacityRecord(scope, original),
            close_open_segment=True,
            recorded_at=datetime(2026, 10, 26, tzinfo=timezone.utc),
        )
        result = repository.save_effective_change(
            P6ResourceCapacityRecord(scope, replacement),
            close_open_segment=True,
            recorded_at=datetime(2026, 10, 27, tzinfo=timezone.utc),
        )

    assert result.superseded_identity == original.identity
    assert result.closed_segment is not None
    assert result.closed_segment.effective_to == date(2026, 10, 31)

    active = repository.list(scope, "CREW-1")
    assert tuple(item.segment.max_units for item in active) == (
        Decimal("8"),
        Decimal("10"),
    )
    profile = ResourceMaxUnitsTimeProfile(
        "CREW-1", tuple(item.segment for item in active)
    )
    assert profile.capacity_on(date(2026, 10, 31)) == Decimal("8")
    assert profile.capacity_on(date(2026, 11, 1)) == Decimal("10")

    # The immutable original row is retained, but no longer part of the
    # effective profile.
    assert repository.get(scope, "CREW-1", original.identity) is None

    with connection.transaction():
        repeated = repository.save_effective_change(
            P6ResourceCapacityRecord(scope, replacement),
            close_open_segment=True,
            recorded_at=datetime(2026, 10, 28, tzinfo=timezone.utc),
        )

    assert repeated.superseded_identity is None
    assert repeated.closed_segment is None
    assert len(repository.list(scope, "CREW-1")) == 2
    supersession_rows = connection.execute(
        "SELECT COUNT(*) FROM p6_resource_capacity_supersession "
        "WHERE tenant_id=%s AND project_id=%s AND resource_id=%s",
        (scope.tenant_id, scope.project_id, "CREW-1"),
    ).fetchone()
    assert supersession_rows[0] == 1


def test_postgres_effective_change_rolls_back_atomically(connection):
    repository = PostgresP6ResourceCapacityRepository(connection)
    repository.initialize()
    scope = _scope()
    original = _segment()
    replacement = _segment(max_units="10", start=date(2026, 11, 1))

    with connection.transaction():
        repository.save_effective_change(
            P6ResourceCapacityRecord(scope, original),
            close_open_segment=True,
            recorded_at=datetime(2026, 10, 26, tzinfo=timezone.utc),
        )

    with pytest.raises(RuntimeError):
        with connection.transaction():
            repository.save_effective_change(
                P6ResourceCapacityRecord(scope, replacement),
                close_open_segment=True,
                recorded_at=datetime(2026, 10, 27, tzinfo=timezone.utc),
            )
            raise RuntimeError("force rollback")

    active = repository.list(scope, "CREW-1")
    assert tuple(item.segment.identity for item in active) == (original.identity,)
