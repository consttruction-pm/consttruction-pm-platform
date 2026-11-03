from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_rate_repository import (
    P6ResourceRateRecord,
    PostgresP6ResourceRateRepository,
)
from construction_pm.resources.models import CostBasis
from construction_pm.resources.rate_facts import ResourceRateFact, ResourceRateProfile


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


def _fact(
    *,
    resource_id: str = "LAB-1",
    rate: str = "80",
    start: date = date(2026, 10, 1),
    end: date | None = None,
    source: str = "manual-entry",
) -> ResourceRateFact:
    return ResourceRateFact.create(
        resource_id=resource_id,
        rate=Decimal(rate),
        basis=CostBasis.PER_HOUR,
        currency="USD",
        unit="hour",
        effective_from=start,
        effective_to=end,
        source=source,
    )


def test_postgres_effective_rate_change_is_append_only_and_idempotent(connection):
    repository = PostgresP6ResourceRateRepository(connection)
    repository.initialize()
    scope = _scope()
    original = _fact()
    replacement = _fact(rate="95", start=date(2026, 11, 1), source="approved-change")

    with connection.transaction():
        repository.save_effective_change(
            P6ResourceRateRecord(scope, original),
            close_open_segment=True,
            recorded_at=datetime(2026, 10, 26, tzinfo=timezone.utc),
        )
        result = repository.save_effective_change(
            P6ResourceRateRecord(scope, replacement),
            close_open_segment=True,
            recorded_at=datetime(2026, 10, 27, tzinfo=timezone.utc),
        )

    assert result.superseded_identity == original.identity
    assert result.closed_fact is not None
    assert result.closed_fact.effective_to == date(2026, 10, 31)

    active = repository.list(scope, "LAB-1")
    assert tuple(item.fact.rate for item in active) == (
        Decimal("80"),
        Decimal("95"),
    )
    profile = ResourceRateProfile("LAB-1", tuple(item.fact for item in active))
    assert profile.fact_on(date(2026, 10, 31)).rate == Decimal("80")
    assert profile.fact_on(date(2026, 11, 1)).rate == Decimal("95")

    # The immutable original row is retained, but no longer part of the
    # effective profile.
    assert repository.get(scope, "LAB-1", original.identity) is None

    with connection.transaction():
        repeated = repository.save_effective_change(
            P6ResourceRateRecord(scope, replacement),
            close_open_segment=True,
            recorded_at=datetime(2026, 10, 28, tzinfo=timezone.utc),
        )

    assert repeated.superseded_identity is None
    assert repeated.closed_fact is None
    assert len(repository.list(scope, "LAB-1")) == 2
    supersession_rows = connection.execute(
        "SELECT COUNT(*) FROM p6_resource_rate_supersession "
        "WHERE tenant_id=%s AND project_id=%s AND resource_id=%s",
        (scope.tenant_id, scope.project_id, "LAB-1"),
    ).fetchone()
    assert supersession_rows[0] == 1


def test_postgres_effective_rate_change_rolls_back_atomically(connection):
    repository = PostgresP6ResourceRateRepository(connection)
    repository.initialize()
    scope = _scope()
    original = _fact()
    replacement = _fact(rate="95", start=date(2026, 11, 1), source="approved-change")

    with connection.transaction():
        repository.save_effective_change(
            P6ResourceRateRecord(scope, original),
            close_open_segment=True,
            recorded_at=datetime(2026, 10, 26, tzinfo=timezone.utc),
        )

    with pytest.raises(RuntimeError):
        with connection.transaction():
            repository.save_effective_change(
                P6ResourceRateRecord(scope, replacement),
                close_open_segment=True,
                recorded_at=datetime(2026, 10, 27, tzinfo=timezone.utc),
            )
            raise RuntimeError("force rollback")

    active = repository.list(scope, "LAB-1")
    assert tuple(item.fact.identity for item in active) == (original.identity,)
