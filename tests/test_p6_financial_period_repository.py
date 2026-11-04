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

    other_tenant = BackendScope("tenant-b", "project-a", 1)
    other_project = BackendScope("tenant-a", "project-b", 1)
    assert repo.get(other_tenant, "2026-09") is None
    assert repo.get(other_project, "2026-09") is None

    with pytest.raises(P6FinancialPeriodPersistenceError, match="REVISION_CONFLICT"):
        repo.get(scope(2), "2026-09")

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


@pytest.mark.parametrize(
    ("start_date", "end_date", "error"),
    [
        ("2026-02-30", "2026-03-31", "INVALID_START_DATE"),
        ("2026-02-01", "2026-02-30", "INVALID_END_DATE"),
        ("2026-10-01", "2026-09-30", "END_DATE_BEFORE_START_DATE"),
        ("20260201", "2026-02-28", "INVALID_START_DATE"),
    ],
)
def test_invalid_period_dates_fail_before_persistence(start_date, end_date, error):
    repo = SQLiteP6FinancialPeriodRepository(sqlite3.connect(":memory:"))
    invalid = P6FinancialPeriod(
        scope(), "invalid-period", "Invalid period", start_date, end_date
    )

    with pytest.raises(P6FinancialPeriodPersistenceError, match=error):
        repo.upsert(invalid)

    assert repo.list(scope()) == ()


def test_valid_leap_day_financial_period_is_accepted():
    leap_period = P6FinancialPeriod(
        scope(), "2024-02", "February 2024", "2024-02-01", "2024-02-29"
    )
    leap_period.validate()
