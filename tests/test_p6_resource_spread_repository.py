from decimal import Decimal
import sqlite3
import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_spread_repository import (
    P6ResourceSpreadBucket,
    P6ResourceSpreadPersistenceError,
    SQLiteP6ResourceSpreadRepository,
)

def scope(revision=1):
    return BackendScope("tenant-a", "project-a", revision)

def bucket(revision=1, spread_id="spread-1", period_id="2026-10"):
    return P6ResourceSpreadBucket(
        scope=scope(revision), spread_id=spread_id, resource_id="resource-1",
        period_id=period_id, period_start="2026-10-01", period_end="2026-10-31",
        spread_type="PLANNED", metric="UNITS", value=Decimal("12.50"), unit="hours",
    )

def test_round_trip_and_deterministic_list():
    repo = SQLiteP6ResourceSpreadRepository(sqlite3.connect(":memory:"))
    first, second = bucket(period_id="2026-11"), bucket(period_id="2026-10")
    assert repo.upsert(first) == first
    assert repo.upsert(second) == second
    assert [x.period_id for x in repo.list(scope())] == ["2026-10", "2026-11"]
    assert repo.get(scope(), "spread-1", "2026-10") == second

def test_scope_isolation_and_revision_conflict():
    repo = SQLiteP6ResourceSpreadRepository(sqlite3.connect(":memory:"))
    repo.upsert(bucket())
    assert repo.get(BackendScope("tenant-b", "project-a", 1), "spread-1", "2026-10") is None
    with pytest.raises(P6ResourceSpreadPersistenceError, match="REVISION_CONFLICT"):
        repo.get(scope(2), "spread-1", "2026-10")

def test_identical_replay_is_idempotent_but_mutation_is_rejected():
    repo = SQLiteP6ResourceSpreadRepository(sqlite3.connect(":memory:"))
    record = bucket()
    assert repo.upsert(record) == record
    assert repo.upsert(record) == record
    changed = P6ResourceSpreadBucket(
        scope=record.scope, spread_id=record.spread_id, resource_id=record.resource_id,
        period_id=record.period_id, period_start=record.period_start, period_end=record.period_end,
        spread_type=record.spread_type, metric=record.metric, value=Decimal("13.50"), unit=record.unit,
    )
    with pytest.raises(P6ResourceSpreadPersistenceError, match="IMMUTABLE_RESOURCE_SPREAD_BUCKET"):
        repo.upsert(changed)

def test_units_and_cost_have_explicit_measurement_metadata():
    repo = SQLiteP6ResourceSpreadRepository(sqlite3.connect(":memory:"))
    with pytest.raises(P6ResourceSpreadPersistenceError, match="CURRENCY_NOT_ALLOWED_FOR_UNITS"):
        repo.upsert(P6ResourceSpreadBucket(
            scope=scope(), spread_id="s", resource_id="r", period_id="p",
            period_start="2026-10-01", period_end="2026-10-31", spread_type="PLANNED",
            metric="UNITS", value=Decimal("1"), unit="hours", currency="USD",
        ))
    with pytest.raises(P6ResourceSpreadPersistenceError, match="UNIT_NOT_ALLOWED_FOR_COST"):
        repo.upsert(P6ResourceSpreadBucket(
            scope=scope(), spread_id="s", resource_id="r", period_id="p",
            period_start="2026-10-01", period_end="2026-10-31", spread_type="PLANNED",
            metric="COST", value=Decimal("1"), currency="USD", unit="hours",
        ))
