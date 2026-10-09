from datetime import date, datetime, timezone

import pytest

from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.schedule_input_snapshot_repository import (
    SQLiteScheduleInputSnapshotRepository,
    build_snapshot,
)
from construction_pm.schedule_snapshot_materializer import materialize_schedule_snapshot
from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import (
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
    ResourceCalendarAssignment,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
)
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.resource_calendar_context import (
    ResourceCalendarContext,
    ResourceCalendarContextError,
)


GLOBAL = CalendarReference("GLOBAL", "3")
PROJECT = CalendarReference("PROJECT", "4")
RESOURCE = CalendarReference("RESOURCE", "8")


def make_snapshot(assignments=(), *, project_id="P1", project_calendar=PROJECT):
    return AuthoritativeScheduleInput(
        snapshot_id=f"snapshot-{project_id}",
        tenant_id="T1",
        project_id=project_id,
        project_revision=7,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=project_calendar,
        activities=(Activity(f"{project_id}-A", 2),),
        relationships=(),
        activity_calendar_assignments=(),
        resource_calendar_assignments=tuple(assignments),
        project_start=date(2026, 10, 1),
    )


def make_registry():
    return CalendarResolverRegistry(
        day_resolvers={
            "GLOBAL@3": WorkingTimeResolver(WorkingCalendar()),
            "PROJECT@4": WorkingTimeResolver(
                WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}))
            ),
            "RESOURCE@8": WorkingTimeResolver(
                WorkingCalendar(working_weekdays=frozenset(range(7)))
            ),
        },
        base_calendar_references={
            "PROJECT@4": GLOBAL,
            "RESOURCE@8": PROJECT,
        },
    )


def test_resource_calendar_assignment_is_versioned_and_changes_snapshot_hash():
    base = make_snapshot()
    assigned = make_snapshot([ResourceCalendarAssignment("R1", RESOURCE)])
    assert assigned.snapshot_hash != base.snapshot_hash
    assert assigned.canonical_payload()["resource_calendar_assignments"] == [
        {
            "resource_id": "R1",
            "calendar": {
                "calendar_id": "RESOURCE",
                "calendar_version": "8",
                "kind": "working-day",
                "system": "gregorian",
            },
        }
    ]


def test_resource_calendar_assignments_reject_duplicate_resource_ids():
    with pytest.raises(ValueError, match="resource calendar assignments must be unique"):
        make_snapshot([
            ResourceCalendarAssignment("R1", RESOURCE),
            ResourceCalendarAssignment("R1", PROJECT),
        ])


def test_resource_calendar_assignment_must_match_snapshot_mode():
    time_calendar = CalendarReference("RESOURCE-TIME", "1", "working-time")
    with pytest.raises(ValueError, match="working-day resource calendars"):
        make_snapshot([ResourceCalendarAssignment("R1", time_calendar)])


def test_resource_calendar_context_resolves_resource_project_global_chain_and_fallback():
    registry = make_registry()
    snapshot = make_snapshot([ResourceCalendarAssignment("R1", RESOURCE)])
    context = ResourceCalendarContext.from_snapshots([snapshot], registry)

    assert context.reference_for_resource("P1", "R1") == RESOURCE
    assert context.for_resource("P1", "R1") is registry.resolve(RESOURCE)
    assert context.reference_for_resource("P1", "R2") == PROJECT
    assert context.for_resource("P1", "R2") is registry.resolve(PROJECT)
    assert context.for_resource("P1", "R1").calendar.working_weekdays == frozenset(range(7))


def test_resource_ids_are_scoped_by_project():
    registry = make_registry()
    project_two_calendar = CalendarReference("PROJECT-2", "1")
    resource_two_calendar = CalendarReference("RESOURCE-2", "1")
    registry = CalendarResolverRegistry(
        day_resolvers={
            "PROJECT@4": WorkingTimeResolver(WorkingCalendar()),
            "RESOURCE@8": WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset(range(7)))),
            "PROJECT-2@1": WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}))),
            "RESOURCE-2@1": WorkingTimeResolver(WorkingCalendar(working_weekdays=frozenset({0, 2, 4}))),
        }
    )
    one = make_snapshot([ResourceCalendarAssignment("R1", RESOURCE)])
    two = make_snapshot(
        [ResourceCalendarAssignment("R1", resource_two_calendar)],
        project_id="P2",
        project_calendar=project_two_calendar,
    )
    context = ResourceCalendarContext.from_snapshots([one, two], registry)
    assert context.reference_for_resource("P1", "R1") == RESOURCE
    assert context.reference_for_resource("P2", "R1") == resource_two_calendar
    assert context.for_resource("P1", "R1").calendar.working_weekdays == frozenset(range(7))
    assert context.for_resource("P2", "R1").calendar.working_weekdays == frozenset({0, 2, 4})


def test_resource_calendar_context_fails_closed_on_missing_resource_calendar():
    missing = CalendarReference("MISSING", "99")
    snapshot = make_snapshot([ResourceCalendarAssignment("R1", missing)])
    with pytest.raises(ResourceCalendarContextError, match="calendar cannot be resolved for resource R1"):
        ResourceCalendarContext.from_snapshots([snapshot], make_registry())


def test_resource_calendar_context_preserves_jalali_calendar_identity():
    jalali_project = CalendarReference("PROJECT-J", "1", system=CalendarSystem.JALALI)
    jalali_resource = CalendarReference("RESOURCE-J", "2", system=CalendarSystem.JALALI)
    registry = CalendarResolverRegistry(
        day_resolvers={
            "PROJECT-J@1": WorkingTimeResolver(WorkingCalendar(system=CalendarSystem.JALALI)),
            "RESOURCE-J@2": WorkingTimeResolver(
                WorkingCalendar(working_weekdays=frozenset(range(7)), system=CalendarSystem.JALALI)
            ),
        },
        base_calendar_references={"RESOURCE-J@2": jalali_project},
    )
    snapshot = make_snapshot(
        [ResourceCalendarAssignment("R1", jalali_resource)],
        project_id="PJ",
        project_calendar=jalali_project,
    )
    context = ResourceCalendarContext.from_snapshots([snapshot], registry)
    assert context.reference_for_resource("PJ", "R1").system is CalendarSystem.JALALI
    assert context.for_resource("PJ", "R1").calendar.system is CalendarSystem.JALALI


def test_snapshot_materializer_round_trips_resource_calendar_assignments():
    import sqlite3

    registry = make_registry()
    source = make_snapshot([ResourceCalendarAssignment("R1", RESOURCE)])
    context = CalculationContext(
        project_id=source.project_id,
        project_version=source.project_revision,
        calendar_id=source.project_calendar.calendar_id,
        calendar_version=source.project_calendar.calendar_version,
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-10-01T08:00:00+00:00",
        input_snapshot_id=source.snapshot_id,
        tenant_id=source.tenant_id,
    )
    conn = sqlite3.connect(":memory:")
    repository = SQLiteScheduleInputSnapshotRepository(conn)
    stored = repository.save(
        build_snapshot(source, context, datetime(2026, 10, 1, 8, tzinfo=timezone.utc))
    )
    materialized = materialize_schedule_snapshot(stored, registry)
    assert materialized.schedule_input.resource_calendar_assignments == (
        ResourceCalendarAssignment("R1", RESOURCE),
    )
    resolved = ResourceCalendarContext.from_snapshots([materialized.schedule_input], registry)
    assert resolved.reference_for_resource("P1", "R1") == RESOURCE
