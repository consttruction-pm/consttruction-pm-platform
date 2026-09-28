import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_financial_period_repository import (
    P6FinancialPeriod,
    P6FinancialPeriodPersistenceError,
    SQLiteP6FinancialPeriodRepository,
)


def scope(revision: int = 1) -> BackendScope:
    return BackendScope("tenant-a", "project-a", revision)


def period(s, period_id="2026-09", status="OPEN"):
    return P6FinancialPeriod(s, period_id, "September 2026", "2026-09-01", "2026-09-30", status)


def test_financial_period_round_trip_and_deterministic_list():
    repo = SQLiteP6FinancialPeriodRepository(sqlite3.connect(":memory:"))
    repo.upsert(period(scope(), "b"))
    repo.upsert(period(scope(), "a"))

    assert repo.get(scope(), "a") == period(scope(), "a")
    assert [p.period_id for p in repo.list(scope())] == ["a", "b"]


def test_scope_isolation_and_revision_conflict():
    repo = SQLiteP6FinancialPeriodRepository(sqlite3.connect(":memory:"))
    repo.upsert(period(scope()))

    assert repo.get(scope(2), "2026-09") is None

    with pytest.raises(P6FinancialPeriodPersistenceError, match="REVISION_CONFLICT"):
        repo.upsert(period(scope(2)))


def test_definition_is_immutable_but_identical_replay_is_idempotent():
    repo = SQLiteP6FinancialPeriodRepository(sqlite3.connect(":memory:"))
    repo.upsert(period(scope()))
    assert repo.upsert(period(scope())) == period(scope())

    with pytest.raises(P6FinancialPeriodPersistenceError, match="IMMUTABLE_FINANCIAL_PERIOD"):
        repo.upsert(
            P6FinancialPeriod(
                scope(), "2026-09", "Changed", "2026-09-01", "2026-09-30", "OPEN"
            )
        )


def test_invalid_status_fails_closed():
    with pytest.raises(P6FinancialPeriodPersistenceError, match="INVALID_STATUS"):
        period(scope(), status="UNKNOWN").validate()
