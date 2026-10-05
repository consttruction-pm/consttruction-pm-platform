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
from construction_pm.calendar_master_repository import CalendarMaster, CalendarPersistenceError, PostgresCalendarMasterRepository
from construction_pm.calendar_snapshot_repository import PostgresCalendarSnapshotRepository
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.scheduling.calendar import WorkingCalendar
from construction_pm.scheduling.calendar_periods import CalendarTimePeriodFactors
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.time_calendar import WorkingTimeCalendar


def scope(revision: int = 7) -> BackendScope:
    suffix = uuid.uuid4().hex
    return BackendScope(f"cal-snapshot-{suffix}", f"project-{suffix}", revision)


def master(s: BackendScope) -> CalendarMaster:
    return CalendarMaster(s, "CAL-1", "1", "working-day", "Project Calendar")


def working_calendar(holiday: date) -> WorkingCalendar:
    return WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}),
        holidays=frozenset({holiday}),
        system=CalendarSystem.JALALI,
        time_period_factors=CalendarTimePeriodFactors(
            hours_per_day=Decimal("8"),
            hours_per_week=Decimal("40"),
            hours_per_month=Decimal("176"),
            hours_per_year=Decimal("2080"),
        ),
    )


def test_postgres_calendar_snapshot_is_immutable_per_calendar_version():
    s = scope()
    calendar = master(s)
    original = working_calendar(date(2026, 3, 21))
    changed = working_calendar(date(2026, 3, 22))

    with psycopg.connect(DSN) as connection:
        masters = PostgresCalendarMasterRepository(connection)
        snapshots = PostgresCalendarSnapshotRepository(connection)
        masters.initialize()
        snapshots.initialize()
        connection.commit()

        with PostgresTransactionManager(connection).transaction():
            masters.save(calendar)
            first = snapshots.save(calendar, original)
            assert snapshots.save(calendar, original) == first

        with pytest.raises(CalendarPersistenceError, match="SNAPSHOT_IMMUTABLE_CONFLICT"):
            with PostgresTransactionManager(connection).transaction():
                snapshots.save(calendar, changed)

        assert snapshots.get(calendar) == first


def test_postgres_working_time_calendar_snapshot_round_trip_preserves_intervals_and_system():
    s = scope()
    calendar = CalendarMaster(s, "CAL-TIME", "1", "working-time", "Time Calendar")
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

    with psycopg.connect(DSN) as connection:
        masters = PostgresCalendarMasterRepository(connection)
        snapshots = PostgresCalendarSnapshotRepository(connection)
        masters.initialize()
        snapshots.initialize()
        connection.commit()

        with PostgresTransactionManager(connection).transaction():
            masters.save(calendar)
            stored = snapshots.save(calendar, definition)

        loaded = snapshots.get(calendar)
        assert loaded == stored
        assert WorkingTimeCalendar.from_canonical_snapshot(loaded.snapshot) == definition
