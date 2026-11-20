"""Fast coverage for the production calendar-registry builder.

The live PostgreSQL proof lives in
``tests/integration/test_p0n2_runtime_activation.py``. These tests use the
SQLite calendar repositories so the fail-closed rules are exercised on every
run, including CI without a database.
"""

from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_exception_repository import (
    SQLiteCalendarExceptionRepository,
)
from construction_pm.calendar_master_repository import (
    CalendarMaster,
    SQLiteCalendarMasterRepository,
)
from construction_pm.calendar_snapshot_repository import (
    SQLiteCalendarSnapshotRepository,
)
from construction_pm.calendar_work_hours_repository import (
    CalendarWorkHourRule,
    SQLiteCalendarWorkHourRepository,
)
from construction_pm.p6_versioned_resource_calendar_resolver import (
    P6ResourceCalendarResolutionError,
    build_calendar_registry_for_scope,
    calendar_registry_hash,
)
from construction_pm.scheduling.calendar import WorkingCalendar
from construction_pm.scheduling.calendar_context import CalendarReference
from construction_pm.scheduling.time_calendar import WorkingTimeCalendar


def _fixture():
    connection = sqlite3.connect(":memory:")
    scope = BackendScope("t1", "p1", 3)
    masters = SQLiteCalendarMasterRepository(connection)
    snapshots = SQLiteCalendarSnapshotRepository(connection)
    work_hours = SQLiteCalendarWorkHourRepository(connection)
    exceptions = SQLiteCalendarExceptionRepository(connection)
    return scope, masters, snapshots, work_hours, exceptions


def _build(scope, masters, snapshots, work_hours, exceptions):
    return build_calendar_registry_for_scope(
        scope=scope,
        calendar_repository=masters,
        snapshot_repository=snapshots,
        exception_repository=exceptions,
        work_hours_repository=work_hours,
    )


def test_builds_registry_from_persisted_definition_and_snapshot():
    scope, masters, snapshots, work_hours, exceptions = _fixture()
    master = masters.save(CalendarMaster(scope, "CAL-1", "1", "working-day", "Project"))
    snapshots.save(master, WorkingCalendar())

    registry = _build(scope, masters, snapshots, work_hours, exceptions)
    assert registry.resolve(CalendarReference("CAL-1", "1")) is not None
    assert calendar_registry_hash(registry) == calendar_registry_hash(
        _build(scope, masters, snapshots, work_hours, exceptions)
    )


def test_weekly_work_hour_rule_changes_the_registered_definition():
    scope, masters, snapshots, work_hours, exceptions = _fixture()
    master = masters.save(CalendarMaster(scope, "CAL-1", "1", "working-day", "Project"))
    snapshots.save(master, WorkingCalendar())
    for weekday in range(7):
        work_hours.save(
            CalendarWorkHourRule(
                scope,
                "CAL-1",
                "1",
                "standard_work_week",
                weekday=weekday,
                is_working_day=weekday < 4,
            )
        )

    registry = _build(scope, masters, snapshots, work_hours, exceptions)
    entry = registry.entries()[0]
    # A four-day week comes from the persisted rule; it is not a registry
    # default and it changes the arithmetic the resolver performs.
    assert entry.snapshot["working_weekdays"] == [0, 1, 2, 3]
    assert registry.resolve(CalendarReference("CAL-1", "1")).next_working_day(
        date(2026, 9, 24)
    ) == date(2026, 9, 28)


def test_missing_snapshot_fails_closed():
    scope, masters, snapshots, work_hours, exceptions = _fixture()
    masters.save(CalendarMaster(scope, "CAL-1", "1", "working-day", "Project"))
    with pytest.raises(P6ResourceCalendarResolutionError, match="CALENDAR_SNAPSHOT_NOT_FOUND"):
        _build(scope, masters, snapshots, work_hours, exceptions)


def test_unsupported_calendar_kind_fails_closed():
    scope, masters, snapshots, work_hours, exceptions = _fixture()
    # The write path rejects this kind, but an imported or hand-edited row can
    # still carry it, so the builder must refuse instead of guessing.
    masters.connection.execute(
        "INSERT INTO calendar_master (tenant_id,project_id,project_revision,calendar_id,"
        "calendar_version,kind,name,record_revision,base_calendar_id,"
        "base_calendar_version,calendar_type) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (scope.tenant_id, scope.project_id, scope.project_revision, "CAL-1", "1",
         "resource", "Resource", 1, None, None, "resource"),
    )
    with pytest.raises(P6ResourceCalendarResolutionError, match="CALENDAR_KIND_UNSUPPORTED"):
        _build(scope, masters, snapshots, work_hours, exceptions)


def test_base_calendar_kind_mismatch_fails_closed():
    scope, masters, snapshots, work_hours, exceptions = _fixture()
    parent = masters.save(CalendarMaster(scope, "PARENT", "1", "working-time", "Parent"))
    snapshots.save(parent, WorkingTimeCalendar())
    child = masters.save(
        CalendarMaster(
            scope,
            "CHILD",
            "1",
            "working-day",
            "Child",
            base_calendar_id="PARENT",
            base_calendar_version="1",
        )
    )
    snapshots.save(child, WorkingCalendar())
    with pytest.raises(P6ResourceCalendarResolutionError, match="CALENDAR_INHERITANCE_KIND_MISMATCH"):
        _build(scope, masters, snapshots, work_hours, exceptions)


def test_scope_isolation_never_resolves_another_project():
    scope, masters, snapshots, work_hours, exceptions = _fixture()
    other = BackendScope("t1", "p2", 3)
    master = masters.save(CalendarMaster(other, "CAL-1", "1", "working-day", "Other"))
    snapshots.save(master, WorkingCalendar())

    registry = _build(scope, masters, snapshots, work_hours, exceptions)
    assert registry.entries() == ()
    with pytest.raises(KeyError):
        registry.resolve(CalendarReference("CAL-1", "1"))
