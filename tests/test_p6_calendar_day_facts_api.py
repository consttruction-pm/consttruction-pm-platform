from __future__ import annotations

import sqlite3
from datetime import date, time

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    RoleBasedAuthorizationPolicy,
    default_role_permissions,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_exception_repository import (
    EXCEPTION_DETAILED_WORK_HOURS,
    EXCEPTION_NONWORK,
    EXCEPTION_RESET_STANDARD,
    EXCEPTION_TOTAL_WORK_HOURS,
    CalendarException as PersistedCalendarException,
    SQLiteCalendarExceptionRepository,
)
from construction_pm.calendar_master_repository import (
    CalendarMaster,
    CalendarPersistenceError,
    SQLiteCalendarMasterRepository,
)
from construction_pm.calendar_snapshot_repository import SQLiteCalendarSnapshotRepository
from construction_pm.calendar_work_hours_repository import SQLiteCalendarWorkHourRepository
from construction_pm.p6_calendar_day_facts_api import (
    P6_CALENDAR_DAY_FACTS_KIND,
    P6_CALENDAR_DAY_FACTS_VERSION,
    P6CalendarDayFactsAPI,
)
from construction_pm.scheduling.calendar import WorkingCalendar
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.time_calendar import WorkingTimeCalendar

SCOPE = BackendScope("tenant-a", "project-a", 7)


@pytest.fixture()
def repos():
    connection = sqlite3.connect(":memory:")
    masters = SQLiteCalendarMasterRepository(connection)
    snapshots = SQLiteCalendarSnapshotRepository(connection)
    exceptions = SQLiteCalendarExceptionRepository(connection)
    work_hours = SQLiteCalendarWorkHourRepository(connection)
    try:
        yield masters, snapshots, exceptions, work_hours
    finally:
        connection.close()


def save_calendar(
    masters,
    snapshots,
    calendar_id: str,
    definition: WorkingCalendar | WorkingTimeCalendar,
    *,
    base: tuple[str, str] | None = None,
):
    kind = "working-time" if isinstance(definition, WorkingTimeCalendar) else "working-day"
    master = masters.save(
        CalendarMaster(
            scope=SCOPE,
            calendar_id=calendar_id,
            calendar_version="1",
            kind=kind,
            name=calendar_id,
            calendar_type="project",
            base_calendar_id=base[0] if base else None,
            base_calendar_version=base[1] if base else None,
        )
    )
    snapshots.save(master, definition)
    return master


def api(repos, *, roles=frozenset({"planner"})):
    masters, snapshots, exceptions, work_hours = repos
    policy = RoleBasedAuthorizationPolicy(default_role_permissions())
    facts = P6CalendarDayFactsAPI(
        calendar_repository=masters,
        snapshot_repository=snapshots,
        exception_repository=exceptions,
        work_hours_repository=work_hours,
        authorization_policy=policy,
    )
    context = AuthorizationContext(
        tenant_id=SCOPE.tenant_id,
        project_id=SCOPE.project_id,
        user_id="user-1",
        roles=roles,
    )
    return facts, context


def weekday_calendar() -> WorkingCalendar:
    # Monday 2026-11-02 through Friday 2026-11-06; 2026-10-28 is a Wednesday.
    return WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}),
        holidays=frozenset({date(2026, 10, 28)}),
    )


def test_no_exceptions_yields_no_overrides(repos):
    masters, snapshots, _exceptions, _work_hours = repos
    save_calendar(masters, snapshots, "CAL", weekday_calendar())
    facts, context = api(repos)

    payload = facts.get_day_facts(SCOPE, "CAL", "1", auth_context=context)

    assert payload["contract_version"] == P6_CALENDAR_DAY_FACTS_VERSION
    assert payload["kind"] == P6_CALENDAR_DAY_FACTS_KIND
    assert payload["overrides"] == []
    assert payload["calendar"] == {
        "calendar_id": "CAL",
        "calendar_version": "1",
        "kind": "working-day",
        "system": "gregorian",
        "record_revision": 1,
    }


def test_nonwork_exception_removes_a_working_day(repos):
    masters, snapshots, exceptions, _work_hours = repos
    save_calendar(masters, snapshots, "CAL", weekday_calendar())
    exceptions.save(
        PersistedCalendarException(
            SCOPE, "CAL", "1", date(2026, 11, 4), EXCEPTION_NONWORK,
            system=CalendarSystem.GREGORIAN,
        )
    )
    facts, context = api(repos)

    payload = facts.get_day_facts(SCOPE, "CAL", "1", auth_context=context)

    assert payload["overrides"] == [
        {"date": "2026-11-04", "working": False, "source": "local"},
    ]


def test_reset_standard_restores_the_stored_definition_rule(repos):
    masters, snapshots, exceptions, _work_hours = repos
    save_calendar(masters, snapshots, "CAL", weekday_calendar())
    exceptions.save(
        PersistedCalendarException(
            SCOPE, "CAL", "1", date(2026, 10, 28), EXCEPTION_RESET_STANDARD,
            system=CalendarSystem.GREGORIAN,
        )
    )
    facts, context = api(repos)

    overrides = facts.get_day_facts(SCOPE, "CAL", "1", auth_context=context)["overrides"]

    # Shared Core defines "standard" as the stored definition's rule. The
    # snapshot marks 2026-10-28 a holiday, so resetting to standard keeps it
    # non-working; the projection must not reinterpret the mode as "remove the
    # holiday".
    assert overrides == [
        {"date": "2026-10-28", "working": False, "source": "local"},
    ]


@pytest.mark.parametrize(
    ("mode", "extra"),
    [
        (EXCEPTION_TOTAL_WORK_HOURS, {"total_work_hours": "4"}),
        (EXCEPTION_DETAILED_WORK_HOURS, {"intervals": ((time(8, 0), time(12, 0)),)}),
    ],
)
def test_hour_overrides_make_a_weekend_working(repos, mode, extra):
    masters, snapshots, exceptions, _work_hours = repos
    save_calendar(masters, snapshots, "CAL", weekday_calendar())
    # 2026-10-31 is a Saturday.
    exceptions.save(
        PersistedCalendarException(
            SCOPE, "CAL", "1", date(2026, 10, 31), mode,
            system=CalendarSystem.GREGORIAN,
            **extra,
        )
    )
    facts, context = api(repos)

    overrides = facts.get_day_facts(SCOPE, "CAL", "1", auth_context=context)["overrides"]

    assert overrides == [
        {"date": "2026-10-31", "working": True, "source": "local"},
    ]


def test_inherited_exception_is_projected_with_inherited_source(repos):
    masters, snapshots, exceptions, _work_hours = repos
    save_calendar(masters, snapshots, "BASE", weekday_calendar())
    save_calendar(masters, snapshots, "CHILD", weekday_calendar(), base=("BASE", "1"))
    exceptions.save(
        PersistedCalendarException(
            SCOPE, "BASE", "1", date(2026, 11, 3), EXCEPTION_NONWORK,
            system=CalendarSystem.GREGORIAN,
        )
    )
    facts, context = api(repos)

    payload = facts.get_day_facts(SCOPE, "CHILD", "1", auth_context=context)

    assert payload["overrides"] == [
        {"date": "2026-11-03", "working": False, "source": "inherited"},
    ]


def test_local_exception_wins_over_same_inherited_date(repos):
    masters, snapshots, exceptions, _work_hours = repos
    save_calendar(masters, snapshots, "BASE", weekday_calendar())
    save_calendar(masters, snapshots, "CHILD", weekday_calendar(), base=("BASE", "1"))
    exceptions.save(
        PersistedCalendarException(
            SCOPE, "BASE", "1", date(2026, 11, 3), EXCEPTION_NONWORK,
            system=CalendarSystem.GREGORIAN,
        )
    )
    exceptions.save(
        PersistedCalendarException(
            SCOPE, "CHILD", "1", date(2026, 11, 3), EXCEPTION_RESET_STANDARD,
            system=CalendarSystem.GREGORIAN,
        )
    )
    facts, context = api(repos)

    overrides = facts.get_day_facts(SCOPE, "CHILD", "1", auth_context=context)["overrides"]

    assert overrides == [
        {"date": "2026-11-03", "working": True, "source": "local"},
    ]


def test_working_time_calendar_uses_interval_capacity(repos):
    masters, snapshots, exceptions, _work_hours = repos
    save_calendar(
        masters,
        snapshots,
        "TIME",
        WorkingTimeCalendar(
            working_weekdays=frozenset({0, 1, 2, 3, 4}),
            daily_intervals={
                weekday: ((time(8, 0), time(12, 0)),)
                for weekday in range(5)
            },
        ),
    )
    exceptions.save(
        PersistedCalendarException(
            SCOPE, "TIME", "1", date(2026, 11, 5), EXCEPTION_NONWORK,
            system=CalendarSystem.GREGORIAN,
        )
    )
    facts, context = api(repos)

    overrides = facts.get_day_facts(SCOPE, "TIME", "1", auth_context=context)["overrides"]

    assert overrides == [
        {"date": "2026-11-05", "working": False, "source": "local"},
    ]


def test_unknown_calendar_fails_without_inventing_facts(repos):
    masters, snapshots, _exceptions, _work_hours = repos
    save_calendar(masters, snapshots, "CAL", weekday_calendar())
    facts, context = api(repos)

    with pytest.raises(CalendarPersistenceError) as excinfo:
        facts.get_day_facts(SCOPE, "MISSING", "1", auth_context=context)
    assert "CALENDAR_NOT_FOUND" in str(excinfo.value)


def test_read_permission_is_required(repos):
    masters, snapshots, _exceptions, _work_hours = repos
    save_calendar(masters, snapshots, "CAL", weekday_calendar())
    facts, context = api(repos, roles=frozenset())

    with pytest.raises(AuthorizationError):
        facts.get_day_facts(SCOPE, "CAL", "1", auth_context=context)


def test_cross_scope_calendar_is_rejected(repos):
    masters, snapshots, _exceptions, _work_hours = repos
    save_calendar(masters, snapshots, "CAL", weekday_calendar())
    facts, context = api(repos)
    other = AuthorizationContext(
        tenant_id=SCOPE.tenant_id,
        project_id="project-b",
        user_id="user-1",
        roles=frozenset({"planner"}),
    )

    with pytest.raises(AuthorizationError):
        facts.get_day_facts(SCOPE, "CAL", "1", auth_context=other)
