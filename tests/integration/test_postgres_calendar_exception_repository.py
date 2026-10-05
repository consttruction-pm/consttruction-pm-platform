import os
import uuid
from datetime import date, time
from decimal import Decimal

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_exception_repository import (
    EXCEPTION_DETAILED_WORK_HOURS,
    EXCEPTION_NONWORK,
    CalendarException,
    PostgresCalendarExceptionRepository,
)
from construction_pm.calendar_master_repository import CalendarMaster, CalendarPersistenceError, PostgresCalendarMasterRepository
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.scheduling.calendar_system import CalendarSystem, JalaliDate


def scope(revision: int = 7) -> BackendScope:
    suffix = uuid.uuid4().hex
    return BackendScope(f"cal-{suffix}", f"project-{suffix}", revision)


def test_postgres_base_reference_and_exception_round_trip():
    s = scope()
    base = CalendarMaster(s, "GLOBAL", "3", "working-day", "Global")
    child = CalendarMaster(s, "PROJECT", "1", "working-day", "Project", base_calendar_id="GLOBAL", base_calendar_version="3")
    with psycopg.connect(DSN) as connection:
        masters = PostgresCalendarMasterRepository(connection)
        exceptions = PostgresCalendarExceptionRepository(connection)
        masters.initialize()
        exceptions.initialize()
        connection.commit()
        with PostgresTransactionManager(connection).transaction():
            masters.save(base)
            masters.save(child)
            stored = exceptions.save(
                CalendarException(
                    s, "PROJECT", "1", JalaliDate(1405, 1, 1), EXCEPTION_NONWORK,
                    system=CalendarSystem.JALALI,
                )
            )
        assert masters.get(s, "PROJECT", "1").base_calendar_id == "GLOBAL"
        assert exceptions.get(s, "PROJECT", "1", date(2026, 3, 21)) == stored
        assert stored.exception_date == date(2026, 3, 21)


def test_postgres_exception_round_trip_preserves_detailed_intervals_and_is_immutable():
    s = scope()
    calendar = CalendarMaster(s, "CAL-1", "1", "working-time", "Time Calendar")
    item = CalendarException(
        s, "CAL-1", "1", date(2026, 3, 22), EXCEPTION_DETAILED_WORK_HOURS,
        intervals=((time(8), time(12)), (time(13), time(17))),
    )
    with psycopg.connect(DSN) as connection:
        masters = PostgresCalendarMasterRepository(connection)
        exceptions = PostgresCalendarExceptionRepository(connection)
        masters.initialize()
        exceptions.initialize()
        connection.commit()
        with PostgresTransactionManager(connection).transaction():
            masters.save(calendar)
            first = exceptions.save(item)
        assert exceptions.save(item) == first
        assert exceptions.get(s, "CAL-1", "1", date(2026, 3, 22)) == first
        changed = CalendarException(
            s, "CAL-1", "1", date(2026, 3, 22), EXCEPTION_NONWORK,
        )
        with pytest.raises(CalendarPersistenceError, match="EXCEPTION_IMMUTABLE_CONFLICT"):
            exceptions.save(changed)
