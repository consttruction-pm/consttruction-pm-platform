import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_master_repository import CalendarMaster, CalendarPersistenceError, SQLiteCalendarMasterRepository
from construction_pm.calendar_snapshot_repository import SQLiteCalendarSnapshotRepository
from construction_pm.scheduling.calendar import WorkingCalendar
from construction_pm.scheduling.calendar_periods import CalendarTimePeriodFactors
from construction_pm.scheduling.calendar_system import CalendarSystem


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("T-1", "P-1", revision)


def master() -> CalendarMaster:
    return CalendarMaster(scope(), "CAL-1", "1", "working-day", "Project Calendar")


def working_calendar() -> WorkingCalendar:
    return WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}),
        holidays=frozenset({date(2026, 3, 21)}),
        system=CalendarSystem.JALALI,
        time_period_factors=CalendarTimePeriodFactors(
            hours_per_day=Decimal("8"),
            hours_per_week=Decimal("40"),
            hours_per_month=Decimal("176"),
            hours_per_year=Decimal("2080"),
        ),
    )


def test_sqlite_snapshot_round_trip_reconstructs_shared_core_calendar():
    conn = sqlite3.connect(":memory:")
    SQLiteCalendarMasterRepository(conn).save(master())
    repo = SQLiteCalendarSnapshotRepository(conn)

    stored = repo.save(master(), working_calendar())
    loaded = repo.get(master())

    assert loaded == stored
    assert loaded is not None
    assert WorkingCalendar.from_canonical_snapshot(loaded.snapshot) == working_calendar()


def test_sqlite_snapshot_json_is_deterministic_and_preserves_decimal_factors():
    conn = sqlite3.connect(":memory:")
    SQLiteCalendarMasterRepository(conn).save(master())
    repo = SQLiteCalendarSnapshotRepository(conn)
    repo.save(master(), working_calendar())

    raw = conn.execute(
        "SELECT snapshot_json FROM calendar_master_snapshot "
        "WHERE tenant_id=? AND project_id=? AND calendar_id=? AND calendar_version=?",
        ("T-1", "P-1", "CAL-1", "1"),
    ).fetchone()[0]

    assert '"hours_per_day":"8"' in raw
    assert raw == (
        '{"holidays":["2026-03-21"],'
        '"system":"jalali",'
        '"time_period_factors":{"hours_per_day":"8","hours_per_month":"176",'
        '"hours_per_week":"40","hours_per_year":"2080"},'
        '"working_weekdays":[0,1,2,3,4]}'
    )


def test_snapshot_read_rejects_stale_project_revision():
    conn = sqlite3.connect(":memory:")
    SQLiteCalendarMasterRepository(conn).save(master())
    repo = SQLiteCalendarSnapshotRepository(conn)
    repo.save(master(), working_calendar())

    with pytest.raises(CalendarPersistenceError, match="REVISION_CONFLICT"):
        repo.get(CalendarMaster(scope(8), "CAL-1", "1", "working-day", "Project Calendar"))


def test_snapshot_repository_requires_authoritative_calendar_reference():
    conn = sqlite3.connect(":memory:")
    SQLiteCalendarMasterRepository(conn).save(master())
    repo = SQLiteCalendarSnapshotRepository(conn)

    assert repo.get(CalendarMaster(scope(), "CAL-2", "1")) is None
