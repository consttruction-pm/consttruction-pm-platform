import sqlite3
from datetime import date, time
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_exception_repository import (
    EXCEPTION_DETAILED_WORK_HOURS,
    EXCEPTION_NONWORK,
    EXCEPTION_RESET_STANDARD,
    EXCEPTION_TOTAL_WORK_HOURS,
    CalendarException,
    SQLiteCalendarExceptionRepository,
)
from construction_pm.calendar_master_repository import (
    CalendarMaster,
    CalendarPersistenceError,
    SQLiteCalendarMasterRepository,
)
from construction_pm.scheduling.calendar_system import CalendarSystem, JalaliDate


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("T-1", "P-1", revision)


def master(**kwargs: object) -> CalendarMaster:
    return CalendarMaster(scope(), "CAL-1", "1", "working-day", "Project Calendar", **kwargs)


def test_base_calendar_reference_round_trip_and_validation():
    repo = SQLiteCalendarMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(master(base_calendar_id="GLOBAL", base_calendar_version="3"))
    loaded = repo.get(scope(), "CAL-1", "1")
    assert loaded == stored
    assert loaded.base_calendar_id == "GLOBAL"
    assert loaded.base_calendar_version == "3"


def test_base_calendar_reference_requires_complete_pair_and_rejects_self():
    with pytest.raises(CalendarPersistenceError, match="INCOMPLETE_BASE_CALENDAR_REFERENCE"):
        master(base_calendar_id="GLOBAL").validate()
    with pytest.raises(CalendarPersistenceError, match="CALENDAR_CANNOT_INHERIT_ITSELF"):
        master(base_calendar_id="CAL-1", base_calendar_version="1").validate()


def test_exception_jalali_and_gregorian_inputs_canonicalize_to_same_date():
    jalali = JalaliDate(1405, 1, 1)
    gregorian = date(2026, 3, 21)
    j = CalendarException(scope(), "CAL-1", "1", jalali, EXCEPTION_NONWORK, system=CalendarSystem.JALALI)
    g = CalendarException(scope(), "CAL-1", "1", gregorian, EXCEPTION_NONWORK)
    assert j.exception_date == g.exception_date
    assert j.canonical_snapshot()["date"] == g.canonical_snapshot()["date"]


def test_sqlite_exception_round_trip_supports_all_override_modes():
    conn = sqlite3.connect(":memory:")
    SQLiteCalendarMasterRepository(conn).save(master())
    repo = SQLiteCalendarExceptionRepository(conn)
    exceptions = (
        CalendarException(scope(), "CAL-1", "1", date(2026, 3, 21), EXCEPTION_NONWORK),
        CalendarException(scope(), "CAL-1", "1", date(2026, 3, 22), EXCEPTION_TOTAL_WORK_HOURS, Decimal("6")),
        CalendarException(
            scope(), "CAL-1", "1", date(2026, 3, 23), EXCEPTION_DETAILED_WORK_HOURS,
            intervals=((time(8), time(12)), (time(13), time(16))),
        ),
        CalendarException(scope(), "CAL-1", "1", date(2026, 3, 24), EXCEPTION_RESET_STANDARD),
    )
    for item in exceptions:
        assert repo.save(item).record_revision == 1
    loaded = repo.list(scope(), "CAL-1", "1")
    assert [item.mode for item in loaded] == [
        EXCEPTION_NONWORK, EXCEPTION_TOTAL_WORK_HOURS,
        EXCEPTION_DETAILED_WORK_HOURS, EXCEPTION_RESET_STANDARD,
    ]
    assert loaded[2].intervals == ((time(8), time(12)), (time(13), time(16)))


def test_exception_save_is_idempotent_and_immutable_per_calendar_version():
    conn = sqlite3.connect(":memory:")
    SQLiteCalendarMasterRepository(conn).save(master())
    repo = SQLiteCalendarExceptionRepository(conn)
    original = CalendarException(scope(), "CAL-1", "1", date(2026, 3, 21), EXCEPTION_NONWORK)
    assert repo.save(original) == repo.save(original)
    changed = CalendarException(scope(), "CAL-1", "1", date(2026, 3, 21), EXCEPTION_TOTAL_WORK_HOURS, Decimal("6"))
    with pytest.raises(CalendarPersistenceError, match="EXCEPTION_IMMUTABLE_CONFLICT"):
        repo.save(changed)


def test_exception_scope_and_revision_are_enforced():
    conn = sqlite3.connect(":memory:")
    SQLiteCalendarMasterRepository(conn).save(master())
    repo = SQLiteCalendarExceptionRepository(conn)
    repo.save(CalendarException(scope(), "CAL-1", "1", date(2026, 3, 21), EXCEPTION_NONWORK))
    with pytest.raises(CalendarPersistenceError, match="REVISION_CONFLICT"):
        repo.get(scope(8), "CAL-1", "1", date(2026, 3, 21))


def test_exception_requires_existing_calendar_master():
    conn = sqlite3.connect(":memory:")
    repo = SQLiteCalendarExceptionRepository(conn)
    with pytest.raises(CalendarPersistenceError, match="CALENDAR_NOT_FOUND"):
        repo.save(CalendarException(scope(), "CAL-1", "1", date(2026, 3, 21), EXCEPTION_NONWORK))


def test_exception_version_is_part_of_identity():
    conn = sqlite3.connect(":memory:")
    master_repo = SQLiteCalendarMasterRepository(conn)
    master_repo.save(master())
    master_repo.save(CalendarMaster(scope(), "CAL-1", "2", "working-day", "Project Calendar"))
    repo = SQLiteCalendarExceptionRepository(conn)
    first = CalendarException(scope(), "CAL-1", "1", date(2026, 3, 21), EXCEPTION_NONWORK)
    second = CalendarException(scope(), "CAL-1", "2", date(2026, 3, 21), EXCEPTION_RESET_STANDARD)
    repo.save(first)
    repo.save(second)
    assert repo.get(scope(), "CAL-1", "1", date(2026, 3, 21)).mode == EXCEPTION_NONWORK
    assert repo.get(scope(), "CAL-1", "2", date(2026, 3, 21)).mode == EXCEPTION_RESET_STANDARD
