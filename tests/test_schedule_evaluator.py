from dataclasses import replace
from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest

from construction_pm.schedule_evaluator import (
    ScheduleEvaluationError,
    evaluate_schedule_snapshot,
)
from construction_pm.schedule_input_snapshot_repository import build_snapshot
from construction_pm.scheduling.activity import Activity, ActivityType
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
    SchedulingCalendarContext,
)
from construction_pm.scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.constraints import ActivityConstraint, ConstraintType
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.resource_dependent import (
    ResourceDependentDemandPeriod,
    ResourceDependentDriverFact,
)
from construction_pm.scheduling.resource_leveling import (
    LevelingActivity,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingOptions,
)
from construction_pm.scheduling.relationships import Relationship
from construction_pm.scheduling.schedule_options import ScheduleMode, ScheduleOptions
from construction_pm.scheduling.time_calendar import TimeAwareWorkingTimeResolver, WorkingTimeCalendar
from construction_pm.scheduling.time_duration import TimeQuantity
from construction_pm.scheduling.time_forward_pass import TimeActivity, TimeRelationship
from construction_pm.scheduling.relationships import RelationshipType


def make_snapshot_and_context(*, options: ScheduleOptions = ScheduleOptions()):
    calendar = CalendarReference("CAL-1", "1")
    source = AuthoritativeScheduleInput(
        snapshot_id="S-H",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=7,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=calendar,
        activities=(Activity("A", 2), Activity("B", 1)),
        relationships=(Relationship("A", "B"),),
        activity_calendar_assignments=(),
        constraints=(
            ActivityConstraint(
                "B",
                ConstraintType.START_NO_EARLIER_THAN,
                date(2026, 9, 23),
            ),
        ),
        schedule_options=options,
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id="P-1",
        project_version=7,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00",
        input_snapshot_id="S-H",
        tenant_id="T-1",
    )
    snapshot = build_snapshot(
        source,
        context,
        datetime(2026, 9, 30, tzinfo=timezone.utc),
    )
    return snapshot, context


def registry():
    return CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )


def test_evaluator_runs_real_date_based_scheduling_core():
    snapshot, context = make_snapshot_and_context()
    result = evaluate_schedule_snapshot(snapshot, context, registry())

    assert result.date_result is not None
    assert result.date_result.activities["A"].start == date(2026, 9, 21)
    assert result.date_result.activities["B"].start == date(2026, 9, 23)
    assert result.project_finish == date(2026, 9, 23)
    assert result.calculation_identity == context.calculation_identity
    assert len(result.calculation_run_identity) == 64

 
def test_evaluator_applies_versioned_activity_calendar_assignments():
    project_calendar = CalendarReference("CAL-1", "1")
    activity_calendar = CalendarReference("CAL-A", "4")
    source = AuthoritativeScheduleInput(
        snapshot_id="S-ACTIVITY-CALENDAR",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=7,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=project_calendar,
        activities=(Activity("A", 2),),
        relationships=(),
        activity_calendar_assignments=(
            ActivityCalendarAssignment("A", activity_calendar),
        ),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id="P-1",
        project_version=7,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00",
        input_snapshot_id="S-ACTIVITY-CALENDAR",
        tenant_id="T-1",
    )
    snapshot = build_snapshot(
        source, context, datetime(2026, 9, 30, tzinfo=timezone.utc)
    )
    calendars = CalendarResolverRegistry(
        day_resolvers={
            "CAL-1@1": WorkingTimeResolver(WorkingCalendar()),
            "CAL-A@4": WorkingTimeResolver(
                WorkingCalendar(working_weekdays=frozenset({1, 2, 3}))
            ),
        }
    )

    result = evaluate_schedule_snapshot(snapshot, context, calendars)

    assert result.date_result is not None
    assert result.date_result.activities["A"].start == date(2026, 9, 22)
    assert result.date_result.activities["A"].finish == date(2026, 9, 23)


def test_evaluator_is_deterministic_for_same_snapshot_and_context():
    snapshot, context = make_snapshot_and_context()
    first = evaluate_schedule_snapshot(snapshot, context, registry())
    second = evaluate_schedule_snapshot(snapshot, context, registry())

    assert first.calculation_run_identity == second.calculation_run_identity
    assert first.date_result == second.date_result


def test_evaluator_replays_same_snapshot_across_provenance_metadata():
    snapshot, context = make_snapshot_and_context()
    replay_context = CalculationContext(
        **{
            **context.to_dict(),
            "calculation_timestamp": "2026-10-01T00:00:00+00:00",
            "actor_id": "actor-replay",
            "request_id": "request-replay",
            "idempotency_key": "idem-replay",
        }
    )

    first = evaluate_schedule_snapshot(snapshot, context, registry())
    replay = evaluate_schedule_snapshot(snapshot, replay_context, registry())

    assert context.calculation_identity == replay_context.calculation_identity
    assert first.calculation_identity == replay.calculation_identity
    assert first.calculation_run_identity == replay.calculation_run_identity
    assert first.date_result == replay.date_result


def test_evaluator_routes_leveling_options_to_authoritative_seam():
    options = ScheduleOptions(
        level_all_resources=True,
        preserve_scheduled_early_and_late_dates=True,
    )
    snapshot, context = make_snapshot_and_context(options=options)
    demand_a = ResourceDemand("R1", date(2026, 9, 21), Decimal("1"), "A")
    demand_b = ResourceDemand("R1", date(2026, 9, 21), Decimal("1"), "B")
    activity_a = LevelingActivity(
        "A", date(2026, 9, 21), date(2026, 9, 22), 1, (demand_a,)
    )
    activity_b = LevelingActivity(
        "B", date(2026, 9, 21), date(2026, 9, 22), 1, (demand_b,)
    )
    leveling_input = SchedulerLevelingInput(
        forward_activities=(activity_a, activity_b),
        backward_activities=(activity_a, activity_b),
        capacities=(
            ResourceCapacity("R1", date(2026, 9, 21), Decimal("1")),
            # The authoritative CPM schedule constrains B to start on Sep 23;
            # final-load validation needs capacity at that actual scheduled date.
            ResourceCapacity("R1", date(2026, 9, 23), Decimal("1")),
            # The authoritative CPM result places B on Sep 25 after its
            # start constraint and duration are propagated; validate that date.
            ResourceCapacity("R1", date(2026, 9, 25), Decimal("1")),
        ),
        options=ResourceLevelingOptions(level_all_resources=True),
    )

    result = evaluate_schedule_snapshot(
        snapshot,
        context,
        registry(),
        leveling_input=leveling_input,
    )

    assert result.date_result is not None
    assert len(result.date_result.activities) == 2
    assert len({item.start for item in result.date_result.activities.values()}) == 2


def test_evaluator_places_alap_assignments_backward_from_cpm_early_and_late_dates():
    calendar = CalendarReference("CAL-1", "1")
    fact = ResourceDependentDriverFact(
        assignment_id="RD-ALAP-ND",
        activity_id="A",
        resource_id="R-RD",
        calendar_id="CAL-1",
        calendar_version="1",
        unit_of_measure="labor-unit",
        planned_units=Decimal("8"),
        is_driving=False,
        units_per_time=Decimal("4"),
        units_per_time_period="day",
        hours_per_units_time_period=Decimal("8"),
        demand_periods=(
            ResourceDependentDemandPeriod(date(2026, 9, 21), Decimal("4")),
            ResourceDependentDemandPeriod(date(2026, 9, 22), Decimal("4")),
        ),
    )
    source = AuthoritativeScheduleInput(
        snapshot_id="S-ALAP",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=7,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=calendar,
        activities=(
            Activity("A", 2, activity_type=ActivityType.RESOURCE_DEPENDENT),
            Activity("B", 1),
        ),
        relationships=(Relationship("A", "B"),),
        activity_calendar_assignments=(),
        schedule_options=ScheduleOptions(mode=ScheduleMode.ALAP),
        project_start=date(2026, 9, 21),
        project_finish=date(2026, 9, 30),
        resource_dependent_assignment_facts=(fact,),
    )
    context = CalculationContext(
        project_id="P-1",
        project_version=7,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00",
        input_snapshot_id="S-ALAP",
        tenant_id="T-1",
    )
    snapshot = build_snapshot(
        source,
        context,
        datetime(2026, 9, 30, tzinfo=timezone.utc),
    )
    capacity_days = (
        "2026-09-21",
        "2026-09-22",
        "2026-09-23",
        "2026-09-24",
        "2026-09-25",
        "2026-09-28",
        "2026-09-29",
        "2026-09-30",
    )
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", date(2026, 9, 21), date(2026, 9, 22), 2),
            LevelingActivity("B", date(2026, 9, 23), date(2026, 9, 23), 1),
        ),
        backward_activities=(
            LevelingActivity("A", date(2026, 9, 28), date(2026, 9, 29), 2),
            LevelingActivity("B", date(2026, 9, 30), date(2026, 9, 30), 1),
        ),
        capacities=tuple(
            ResourceCapacity(
                "R-RD",
                date.fromisoformat(day),
                Decimal("8"),
                "CAL-1",
                "1",
                "b" * 64,
            )
            for day in capacity_days
        ),
        options=ResourceLevelingOptions(),
    )

    result = evaluate_schedule_snapshot(
        snapshot,
        context,
        registry(),
        leveling_input=leveling_input,
    )

    assert result.date_result is not None
    # ALAP schedules the activities at their CPM late dates.
    assert result.date_result.activities["A"].start == date(2026, 9, 28)
    assert result.date_result.activities["B"].start == date(2026, 9, 30)
    placement = result.resource_dependent_placement
    assert placement is not None
    assert placement.status == "COMPLETE"
    assert placement.placement_direction == "LATE"
    placed = placement.assignments[0]
    assert (placed.start, placed.finish) == (date(2026, 9, 28), date(2026, 9, 29))
    assert (placed.early_start, placed.early_finish) == (
        date(2026, 9, 21),
        date(2026, 9, 22),
    )
    assert (placed.late_start, placed.late_finish) == (
        date(2026, 9, 28),
        date(2026, 9, 29),
    )
    assert placed.assignment_float_working_days == 5

    # The P6 Level Resources preservation option controls activity-level
    # backward leveling; it does not force each nondriving assignment into its
    # late CPM window. Assignment placement direction follows ScheduleMode.
    def evaluate_earliest_with_preservation(*, snapshot_id: str, preserve: bool):
        configured_source = replace(
            source,
            snapshot_id=snapshot_id,
            schedule_options=ScheduleOptions(
                mode=ScheduleMode.EARLIEST,
                level_all_resources=True,
                preserve_scheduled_early_and_late_dates=preserve,
            ),
        )
        configured_context = replace(context, input_snapshot_id=snapshot_id)
        configured_snapshot = build_snapshot(
            configured_source,
            configured_context,
            datetime(2026, 9, 30, tzinfo=timezone.utc),
        )
        return evaluate_schedule_snapshot(
            configured_snapshot,
            configured_context,
            registry(),
            leveling_input=leveling_input,
        )

    backward_levelled = evaluate_earliest_with_preservation(
        snapshot_id="S-EARLIEST-BACKWARD-LEVEL",
        preserve=False,
    )
    assert backward_levelled.date_result is not None
    assert backward_levelled.date_result.mode is ScheduleMode.EARLIEST
    backward_placement = backward_levelled.resource_dependent_placement
    assert backward_placement is not None
    assert backward_placement.status == "COMPLETE"
    assert backward_placement.placement_direction == "EARLY"
    backward_assignment = backward_placement.assignments[0]
    assert (backward_assignment.start, backward_assignment.finish) == (
        backward_assignment.early_start,
        backward_assignment.early_finish,
    )

    forward_levelled = evaluate_earliest_with_preservation(
        snapshot_id="S-EARLIEST-PRESERVED",
        preserve=True,
    )
    assert forward_levelled.date_result is not None
    assert forward_levelled.date_result.mode is ScheduleMode.EARLIEST
    forward_placement = forward_levelled.resource_dependent_placement
    assert forward_placement is not None
    assert forward_placement.status == "COMPLETE"
    assert forward_placement.placement_direction == "EARLY"
    forward_assignment = forward_placement.assignments[0]
    assert (forward_assignment.start, forward_assignment.finish) == (
        forward_assignment.early_start,
        forward_assignment.early_finish,
    )


def test_evaluator_rejects_leveling_request_without_authoritative_leveling_input():
    options = ScheduleOptions(level_all_resources=True)
    snapshot, context = make_snapshot_and_context(options=options)

    with pytest.raises(ScheduleEvaluationError, match="SCHEDULE_LEVELING_INPUT_REQUIRED"):
        evaluate_schedule_snapshot(snapshot, context, registry())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("input_snapshot_id", "OTHER"),
        ("project_version", 8),
        ("project_id", "OTHER"),
        ("tenant_id", "OTHER"),
    ],
)
def test_evaluator_rejects_context_scope_mismatch(field, value):
    snapshot, context = make_snapshot_and_context()
    values = context.to_dict()
    values[field] = value
    mismatched = CalculationContext(**values)
    with pytest.raises(ScheduleEvaluationError):
        evaluate_schedule_snapshot(snapshot, mismatched, registry())


def test_evaluator_rejects_unregistered_authoritative_calendar():
    snapshot, context = make_snapshot_and_context()
    with pytest.raises(ScheduleEvaluationError, match="SCHEDULE_EVALUATION_FAILED"):
        evaluate_schedule_snapshot(snapshot, context, CalendarResolverRegistry())


def test_evaluator_routes_time_aware_mode_through_full_shared_schedule_core():
    calendar = CalendarReference('CAL-T', '1', 'working-time')
    working_calendar = WorkingTimeCalendar(
        daily_intervals={i: ((time(8), time(12)), (time(13), time(17))) for i in range(5)}
    )
    registry = CalendarResolverRegistry(
        time_resolvers={'CAL-T@1': TimeAwareWorkingTimeResolver(working_calendar)}
    )
    context_ref = SchedulingCalendarContext(
        project=calendar, activity=calendar, relationship_lag=calendar
    )
    source = AuthoritativeScheduleInput(
        snapshot_id='S-T',
        tenant_id='T-1',
        project_id='P-1',
        project_revision=7,
        mode=AuthoritativeScheduleMode.TIME_AWARE,
        project_calendar=calendar,
        activities=(
            TimeActivity('A', TimeQuantity.working_hours(4), context_ref),
            TimeActivity('B', TimeQuantity.working_hours(2), context_ref),
        ),
        relationships=(TimeRelationship('A', 'B', RelationshipType.FS),),
        activity_calendar_assignments=(),
        project_start=datetime(2026, 9, 22, 8, tzinfo=timezone.utc),
        project_finish=datetime(2026, 9, 22, 17, tzinfo=timezone.utc),
    )
    calc_context = CalculationContext(
        project_id='P-1', project_version=7, calendar_id='CAL-T', calendar_version='1',
        rules_version='rules-1', engine_version='engine-1', timezone='UTC',
        calculation_timestamp='2026-09-30T00:00:00+00:00', input_snapshot_id='S-T', tenant_id='T-1',
    )
    snapshot = build_snapshot(source, calc_context, datetime(2026, 9, 30, tzinfo=timezone.utc))

    result = evaluate_schedule_snapshot(snapshot, calc_context, registry)

    assert result.time_result is not None
    assert result.time_activities == result.time_result.early_activities
    assert result.time_result.late_activities['B'].finish == datetime(2026, 9, 22, 17, tzinfo=timezone.utc)
    assert result.time_result.floats['B'].total_float_hours == Decimal('2')
