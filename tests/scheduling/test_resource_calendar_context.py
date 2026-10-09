from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import sqlite3

import pytest

from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.schedule_input_snapshot_repository import (
    ScheduleInputSnapshot,
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
from construction_pm.scheduling.resource_leveling import (
    BackwardLevelingActivity,
    LevelingActivity,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingOptions,
    propose_backward_leveling,
    propose_forward_leveling_within_float,
)
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.schedule import ScheduleOptions
from construction_pm.scheduling.authoritative_schedule_batch import execute_authoritative_schedule_batch


GLOBAL = CalendarReference("GLOBAL", "3")
PROJECT = CalendarReference("PROJECT", "4")
RESOURCE = CalendarReference("RESOURCE", "8")


def make_snapshot(
    assignments=(),
    *,
    project_id="P1",
    project_calendar=PROJECT,
    project_start=date(2026, 10, 1),
    project_finish=date(2026, 10, 20),
    schedule_options=ScheduleOptions(),
):
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
        project_start=project_start,
        project_finish=project_finish,
        schedule_options=schedule_options,
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

def test_snapshot_materializer_accepts_legacy_payload_without_resource_assignments():
    source = make_snapshot()
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
    original = build_snapshot(
        source, context, datetime(2026, 10, 1, 8, tzinfo=timezone.utc)
    )
    payload = json.loads(original.canonical_payload)
    payload.pop("resource_calendar_assignments")
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    legacy = ScheduleInputSnapshot(
        scope=original.scope,
        snapshot_id=original.snapshot_id,
        snapshot_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        canonical_payload=canonical,
        calculation_identity=original.calculation_identity,
        created_at=original.created_at,
        calculation_identity_version=original.calculation_identity_version,
    )
    materialized = materialize_schedule_snapshot(legacy, make_registry())
    assert materialized.schedule_input.resource_calendar_assignments == ()

def test_forward_leveling_shifts_demand_with_resource_calendar_not_project_calendar():
    project_resolver = WorkingTimeResolver(WorkingCalendar())
    resource_resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset(range(7)))
    )
    demand = ResourceDemand("R1", date(2026, 10, 2), Decimal("1"), "A")
    activity = LevelingActivity(
        activity_id="A",
        start=date(2026, 10, 2),
        finish=date(2026, 10, 2),
        total_float=3,
        resource_demands=(demand,),
    )
    capacities = (
        ResourceCapacity("R1", date(2026, 10, 2), Decimal("0")),
        ResourceCapacity("R1", date(2026, 10, 3), Decimal("1")),
        ResourceCapacity("R1", date(2026, 10, 5), Decimal("0")),
        ResourceCapacity("R1", date(2026, 10, 6), Decimal("1")),
    )

    project_only = propose_forward_leveling_within_float(
        (activity,), capacities, resolver=project_resolver
    )
    resource_aware = propose_forward_leveling_within_float(
        (activity,),
        capacities,
        resolver=project_resolver,
        resource_calendar_resolvers={"R1": resource_resolver},
    )

    assert project_only[0].shift_working_days == 2
    assert resource_aware[0].shift_working_days == 1
    # Activity dates remain on the activity/project calendar; only demand
    # bucket movement uses the resource-specific calendar.
    assert resource_aware[0].new_start == date(2026, 10, 5)


def test_backward_leveling_shifts_demand_with_resource_calendar_not_project_calendar():
    project_resolver = WorkingTimeResolver(WorkingCalendar())
    resource_resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset(range(7)))
    )
    demand = ResourceDemand("R1", date(2026, 10, 5), Decimal("1"), "A")
    activity = BackwardLevelingActivity(
        activity_id="A",
        early_start=date(2026, 10, 1),
        early_finish=date(2026, 10, 1),
        late_start=date(2026, 10, 5),
        late_finish=date(2026, 10, 5),
        resource_demands=(demand,),
    )
    capacities = (
        ResourceCapacity("R1", date(2026, 10, 5), Decimal("0")),
        ResourceCapacity("R1", date(2026, 10, 4), Decimal("1")),
        ResourceCapacity("R1", date(2026, 10, 2), Decimal("0")),
        ResourceCapacity("R1", date(2026, 10, 1), Decimal("1")),
    )

    project_only = propose_backward_leveling(
        (activity,), capacities, resolver=project_resolver
    )
    resource_aware = propose_backward_leveling(
        (activity,),
        capacities,
        resolver=project_resolver,
        resource_calendar_resolvers={"R1": resource_resolver},
    )

    assert project_only[0].advanced_days == 2
    assert resource_aware[0].advanced_days == 1
    assert resource_aware[0].new_start == date(2026, 10, 4)

def test_resource_calendar_context_preserves_local_inherited_standard_precedence():
    from construction_pm.scheduling.calendar_exception_overlay import CalendarExceptionLayers
    from construction_pm.scheduling.calendar_exceptions import (
        CalendarException,
        CalendarExceptionType,
    )

    inherited_date = date(2026, 10, 8)
    local_reset_date = date(2026, 10, 9)
    registry = CalendarResolverRegistry(
        day_resolvers={
            "GLOBAL@3": WorkingTimeResolver(WorkingCalendar()),
            "PROJECT@4": WorkingTimeResolver(WorkingCalendar()),
            "RESOURCE@8": WorkingTimeResolver(
                WorkingCalendar(working_weekdays=frozenset(range(7)))
            ),
        },
        base_calendar_references={
            "PROJECT@4": GLOBAL,
            "RESOURCE@8": PROJECT,
        },
        exception_layers={
            "GLOBAL@3": CalendarExceptionLayers(
                local=(CalendarException(inherited_date, CalendarExceptionType.NONWORK),)
            ),
            "PROJECT@4": CalendarExceptionLayers(
                local=(
                    CalendarException(
                        inherited_date,
                        CalendarExceptionType.TOTAL_WORK_HOURS,
                        total_work_hours=Decimal("6"),
                    ),
                )
            ),
            "RESOURCE@8": CalendarExceptionLayers(
                local=(
                    CalendarException(local_reset_date, CalendarExceptionType.RESET_TO_STANDARD),
                )
            ),
        },
    )
    snapshot = make_snapshot([ResourceCalendarAssignment("R1", RESOURCE)])
    context = ResourceCalendarContext.from_snapshots([snapshot], registry)
    resolved = context.for_resource("P1", "R1")

    inherited_rule = resolved.calendar.effective_rule(inherited_date)
    local_rule = resolved.calendar.effective_rule(local_reset_date)
    assert inherited_rule.source == "inherited"
    assert inherited_rule.is_working is True
    assert local_rule.source == "local"
    assert local_rule.is_working is True

def test_authoritative_batch_wires_resource_calendar_into_resource_leveling():
    project_calendar = CalendarReference("BATCH-PROJECT", "1")
    resource_calendar = CalendarReference("BATCH-RESOURCE", "1")
    project_resolver = WorkingTimeResolver(WorkingCalendar())
    resource_resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset(range(7)))
    )
    registry = CalendarResolverRegistry(
        day_resolvers={
            "BATCH-PROJECT@1": project_resolver,
            "BATCH-RESOURCE@1": resource_resolver,
        },
        base_calendar_references={"BATCH-RESOURCE@1": project_calendar},
    )
    snapshots = (
        make_snapshot(
            [ResourceCalendarAssignment("R1", resource_calendar)],
            project_id="P1",
            project_calendar=project_calendar,
            project_start=date(2026, 10, 2),
            project_finish=date(2026, 10, 20),
            schedule_options=ScheduleOptions(level_all_resources=True, preserve_scheduled_early_and_late_dates=True),
        ),
        make_snapshot(
            [ResourceCalendarAssignment("R2", resource_calendar)],
            project_id="P2",
            project_calendar=project_calendar,
            project_start=date(2026, 10, 2),
            project_finish=date(2026, 10, 20),
            schedule_options=ScheduleOptions(level_all_resources=True, preserve_scheduled_early_and_late_dates=True),
        ),
    )
    resource_demand = ResourceDemand("R1", date(2026, 10, 2), Decimal("1"), "P1-A")
    forward = (
        LevelingActivity("P1-A", date(2026, 10, 2), date(2026, 10, 2), 3, (resource_demand,)),
        LevelingActivity("P2-A", date(2026, 10, 2), date(2026, 10, 2), 3, ()),
    )
    backward = (
        BackwardLevelingActivity(
            "P1-A", date(2026, 10, 2), date(2026, 10, 2),
            date(2026, 10, 2), date(2026, 10, 2), (resource_demand,),
        ),
        BackwardLevelingActivity(
            "P2-A", date(2026, 10, 2), date(2026, 10, 2),
            date(2026, 10, 2), date(2026, 10, 2), (),
        ),
    )
    leveling_input = SchedulerLevelingInput(
        forward_activities=forward,
        backward_activities=backward,
        capacities=(
            ResourceCapacity("R1", date(2026, 10, 2), Decimal("0")),
            ResourceCapacity("R1", date(2026, 10, 3), Decimal("1")),
            ResourceCapacity("R1", date(2026, 10, 5), Decimal("0")),
            ResourceCapacity("R1", date(2026, 10, 6), Decimal("1")),
        ),
        options=ResourceLevelingOptions(level_all_resources=True),
    )
    project_only = execute_authoritative_schedule_batch(
        snapshots,
        resolvers={"P1": project_resolver, "P2": project_resolver},
        leveling_input=leveling_input,
    )
    resource_aware = execute_authoritative_schedule_batch(
        snapshots,
        resolvers={"P1": project_resolver, "P2": project_resolver},
        leveling_input=leveling_input,
        calendar_registry=registry,
    )
    # Without a registry, demand moves through Monday and Tuesday capacity.
    assert project_only.project("P1").result.activities["P1-A"].start == date(2026, 10, 6)
    # The authoritative resource calendar permits the demand shift on Saturday,
    # while the CPM activity date itself remains on the project working calendar.
    assert resource_aware.project("P1").result.activities["P1-A"].start == date(2026, 10, 5)

