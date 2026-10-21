from __future__ import annotations

import sqlite3
from datetime import date, time
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_exception_repository import (
    CalendarException as PersistedCalendarException,
    EXCEPTION_DETAILED_WORK_HOURS,
    EXCEPTION_NONWORK,
    EXCEPTION_RESET_STANDARD,
)
from construction_pm.calendar_master_repository import (
    CalendarMaster,
    SQLiteCalendarMasterRepository,
)
from construction_pm.calendar_exception_repository import SQLiteCalendarExceptionRepository
from construction_pm.calendar_snapshot_repository import SQLiteCalendarSnapshotRepository
from construction_pm.calendar_work_hours_repository import (
    CalendarWorkHourRule,
    SQLiteCalendarWorkHourRepository,
)
from construction_pm.p6_versioned_resource_calendar_resolver import (
    P6ResourceCalendarResolutionError,
    resolve_p6_resource_calendar,
)
from construction_pm.scheduling.calendar import WorkingCalendar
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.time_calendar import WorkingTimeCalendar


@pytest.fixture()
def repositories():
    connection = sqlite3.connect(":memory:")
    masters = SQLiteCalendarMasterRepository(connection)
    snapshots = SQLiteCalendarSnapshotRepository(connection)
    exceptions = SQLiteCalendarExceptionRepository(connection)
    work_hours = SQLiteCalendarWorkHourRepository(connection)
    scope = BackendScope("tenant-a", "project-a", 7)
    try:
        yield connection, scope, masters, snapshots, exceptions, work_hours
    finally:
        connection.close()


def save_calendar(
    scope: BackendScope,
    masters: SQLiteCalendarMasterRepository,
    snapshots: SQLiteCalendarSnapshotRepository,
    calendar_id: str,
    version: str,
    definition: WorkingCalendar | WorkingTimeCalendar,
    *,
    calendar_type: str = "resource",
    base_calendar_id: str | None = None,
    base_calendar_version: str | None = None,
):
    kind = "working-time" if isinstance(definition, WorkingTimeCalendar) else "working-day"
    master = masters.save(CalendarMaster(
        scope=scope,
        calendar_id=calendar_id,
        calendar_version=version,
        kind=kind,
        name=calendar_id,
        base_calendar_id=base_calendar_id,
        base_calendar_version=base_calendar_version,
        calendar_type=calendar_type,
    ))
    snapshots.save(master, definition)
    return master


def resolve(repositories, calendar_id: str, version: str, periods: tuple[date, ...]):
    _connection, scope, masters, snapshots, exceptions, work_hours = repositories
    return resolve_p6_resource_calendar(
        scope=scope,
        calendar_id=calendar_id,
        calendar_version=version,
        periods=periods,
        calendar_repository=masters,
        snapshot_repository=snapshots,
        exception_repository=exceptions,
        work_hours_repository=work_hours,
    )


def test_exact_version_calendar_resolves_capacity_and_stable_hash(repositories):
    _conn, scope, masters, snapshots, _exceptions, _work_hours = repositories
    save_calendar(
        scope, masters, snapshots, "resource-calendar", "v1",
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4})),
    )
    periods = (date(2026, 10, 1), date(2026, 10, 2))  # Thu, Fri

    first = resolve(repositories, "resource-calendar", "v1", periods)
    second = resolve(repositories, "resource-calendar", "v1", periods)

    assert first.id == "resource-calendar"
    assert first.calendar_version == "v1"
    assert first.canonical_snapshot_hash is not None
    assert len(first.canonical_snapshot_hash) == 64
    assert first.canonical_snapshot_hash == second.canonical_snapshot_hash
    assert first.capacity_slices == (
        (date(2026, 10, 1), Decimal("8")),
        (date(2026, 10, 2), Decimal("8")),
    )


def test_resource_capacity_uses_exact_versioned_workweek_and_nonwork_exception(repositories):
    _conn, scope, masters, snapshots, exceptions, work_hours = repositories
    save_calendar(
        scope, masters, snapshots, "resource-calendar", "v7",
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4})),
    )
    work_hours.save(CalendarWorkHourRule(
        scope, "resource-calendar", "v7", "standard_work_week",
        weekday=0, is_working_day=True, total_work_hours=Decimal("6"),
    ))
    work_hours.save(CalendarWorkHourRule(
        scope, "resource-calendar", "v7", "standard_work_week",
        weekday=4, is_working_day=False, total_work_hours=Decimal("0"),
    ))
    exceptions.save(PersistedCalendarException(
        scope, "resource-calendar", "v7", date(2026, 10, 1),
        EXCEPTION_NONWORK, system=CalendarSystem.GREGORIAN,
    ))

    result = resolve(
        repositories, "resource-calendar", "v7",
        (date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 5)),
    )
    capacity = dict(result.capacity_slices)

    assert capacity[date(2026, 10, 1)] == Decimal("0")  # local exception
    assert capacity[date(2026, 10, 2)] == Decimal("0")  # weekly Friday override
    assert capacity[date(2026, 10, 5)] == Decimal("6")  # Monday hours override


def test_inherited_nonwork_exception_and_local_reset_standard_precedence(repositories):
    _conn, scope, masters, snapshots, exceptions, _work_hours = repositories
    definition = WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}))
    save_calendar(
        scope, masters, snapshots, "global-calendar", "g3", definition,
        calendar_type="global",
    )
    save_calendar(
        scope, masters, snapshots, "resource-calendar", "r2", definition,
        base_calendar_id="global-calendar", base_calendar_version="g3",
    )
    exceptions.save(PersistedCalendarException(
        scope, "global-calendar", "g3", date(2026, 10, 2),
        EXCEPTION_NONWORK, system=CalendarSystem.GREGORIAN,
    ))

    inherited = resolve(
        repositories, "resource-calendar", "r2", (date(2026, 10, 2),)
    )
    assert inherited.capacity_slices == ((date(2026, 10, 2), Decimal("0")),)

    exceptions.save(PersistedCalendarException(
        scope, "resource-calendar", "r2", date(2026, 10, 2),
        EXCEPTION_RESET_STANDARD, system=CalendarSystem.GREGORIAN,
    ))
    overridden = resolve(
        repositories, "resource-calendar", "r2", (date(2026, 10, 2),)
    )
    assert overridden.capacity_slices == ((date(2026, 10, 2), Decimal("8")),)
    assert overridden.canonical_snapshot_hash != inherited.canonical_snapshot_hash


def test_working_time_calendar_applies_date_specific_detailed_hours(repositories):
    _conn, scope, masters, snapshots, exceptions, _work_hours = repositories
    intervals = {
        weekday: ((time(8, 0), time(12, 0)), (time(13, 0), time(17, 0)))
        for weekday in range(5)
    }
    save_calendar(
        scope, masters, snapshots, "time-resource-calendar", "t4",
        WorkingTimeCalendar(
            working_weekdays=frozenset({0, 1, 2, 3, 4}),
            daily_intervals=intervals,
        ),
    )
    exceptions.save(PersistedCalendarException(
        scope,
        "time-resource-calendar",
        "t4",
        date(2026, 10, 1),
        EXCEPTION_DETAILED_WORK_HOURS,
        intervals=((time(9, 0), time(12, 0)), (time(13, 0), time(16, 0))),
        system=CalendarSystem.GREGORIAN,
    ))

    result = resolve(
        repositories, "time-resource-calendar", "t4",
        (date(2026, 10, 1), date(2026, 10, 2)),
    )
    assert dict(result.capacity_slices) == {
        date(2026, 10, 1): Decimal("6"),
        date(2026, 10, 2): Decimal("8"),
    }


@pytest.mark.parametrize(
    "kind,kwargs,expected",
    [
        (
            "detailed_work_hours",
            {"weekday": 4, "intervals": (("08:00", "12:00"),)},
            "DATED_DETAILED_WORK_HOURS_REQUIRE_DATE_KEY",
        ),
        (
            "total_work_hours",
            {"weekday": None, "total_work_hours": Decimal("40")},
            "CALENDAR_TOTAL_WORK_HOURS_MAPPING_UNVERIFIED",
        ),
    ],
)
def test_ambiguous_persisted_work_hour_contract_fails_closed(
    repositories, kind, kwargs, expected
):
    _conn, scope, masters, snapshots, _exceptions, work_hours = repositories
    save_calendar(
        scope, masters, snapshots, "resource-calendar", "v1",
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4})),
    )
    work_hours.save(CalendarWorkHourRule(
        scope, "resource-calendar", "v1", kind, **kwargs
    ))

    with pytest.raises(P6ResourceCalendarResolutionError, match=expected):
        resolve(repositories, "resource-calendar", "v1", (date(2026, 10, 2),))


def test_missing_or_wrong_calendar_version_fails_closed(repositories):
    _conn, scope, masters, snapshots, _exceptions, _work_hours = repositories
    save_calendar(
        scope, masters, snapshots, "resource-calendar", "v1",
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4})),
    )

    with pytest.raises(P6ResourceCalendarResolutionError, match="RESOURCE_CALENDAR_NOT_FOUND"):
        resolve(repositories, "resource-calendar", "v2", (date(2026, 10, 2),))
