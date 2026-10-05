import sqlite3
from datetime import date
from datetime import time
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_master_repository import CalendarMaster, CalendarPersistenceError, SQLiteCalendarMasterRepository
from construction_pm.calendar_snapshot_repository import SQLiteCalendarSnapshotRepository
from construction_pm.scheduling.calendar import WorkingCalendar
from construction_pm.scheduling.calendar_periods import CalendarTimePeriodFactors
from construction_pm.scheduling.time_calendar import WorkingTimeCalendar
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


def test_snapshot_save_is_idempotent_for_same_version_and_rejects_changed_content():
    conn = sqlite3.connect(":memory:")
    SQLiteCalendarMasterRepository(conn).save(master())
    repo = SQLiteCalendarSnapshotRepository(conn)

    original = repo.save(master(), working_calendar())
    assert repo.save(master(), working_calendar()) == original

    changed = WorkingCalendar(
        working_weekdays=working_calendar().working_weekdays,
        holidays=frozenset({date(2026, 3, 22)}),
        system=working_calendar().system,
        time_period_factors=working_calendar().time_period_factors,
    )
    with pytest.raises(CalendarPersistenceError, match="SNAPSHOT_IMMUTABLE_CONFLICT"):
        repo.save(master(), changed)

    assert repo.get(master()) == original


def test_sqlite_time_calendar_snapshot_round_trip_preserves_jalali_and_intervals():
    conn = sqlite3.connect(":memory:")
    calendar = CalendarMaster(scope(), "CAL-TIME", "1", "working-time", "Time Calendar")
    SQLiteCalendarMasterRepository(conn).save(calendar)
    repo = SQLiteCalendarSnapshotRepository(conn)

    definition = WorkingTimeCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}),
        holidays=frozenset({date(2026, 3, 21)}),
        daily_intervals={
            0: ((time(8, 0), time(12, 0)), (time(13, 0), time(17, 0))),
            1: ((time(8, 0), time(17, 0)),),
        },
        system=CalendarSystem.JALALI,
        time_period_factors=CalendarTimePeriodFactors(
            hours_per_day=Decimal("8"),
            hours_per_week=Decimal("40"),
            hours_per_month=Decimal("176"),
            hours_per_year=Decimal("2080"),
        ),
    )

    stored = repo.save(calendar, definition)
    loaded = repo.get(calendar)

    assert loaded == stored
    assert loaded is not None
    assert WorkingTimeCalendar.from_canonical_snapshot(loaded.snapshot) == definition


def test_sqlite_snapshot_rejects_calendar_kind_mismatch():
    conn = sqlite3.connect(":memory:")
    calendar = CalendarMaster(scope(), "CAL-TIME", "1", "working-time", "Time Calendar")
    SQLiteCalendarMasterRepository(conn).save(calendar)
    repo = SQLiteCalendarSnapshotRepository(conn)

    with pytest.raises(CalendarPersistenceError, match="CALENDAR_KIND_MISMATCH"):
        repo.save(calendar, working_calendar())

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
