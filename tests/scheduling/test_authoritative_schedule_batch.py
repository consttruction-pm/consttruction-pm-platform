from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar_context import SchedulingCalendarContext
from construction_pm.scheduling.time_duration import TimeQuantity
from construction_pm.scheduling.time_forward_pass import TimeActivity
from construction_pm.scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.resource_leveling import (
    BackwardLevelingActivity,
    LevelingActivity,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingOptions,
)
from construction_pm.scheduling.authoritative_schedule_batch import (
    UnsupportedMultiProjectSchedulingError,
    execute_authoritative_schedule_batch,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry
from construction_pm.scheduling.constraints import ActivityConstraint, ConstraintType
from construction_pm.scheduling.external_resource_assignments import ExternalResourceAssignment
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.schedule_options import ScheduleOptions


def snapshot(project_id, finish, *, options=None, priority=10):
    reference = CalendarReference('CAL', '1')
    return AuthoritativeScheduleInput(
        snapshot_id=f's-{project_id}',
        tenant_id='tenant',
        project_id=project_id,
        project_revision=1,
        project_leveling_priority=priority,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=reference,
        activities=(Activity(id=f'{project_id}-A', duration=1),),
        relationships=(),
        activity_calendar_assignments=(
            ActivityCalendarAssignment(f'{project_id}-A', reference),
        ),
        project_finish=finish,
        project_start=date(2026, 10, 1),
        schedule_options=options or ScheduleOptions(),
    )


def resolver():
    return WorkingTimeResolver(WorkingCalendar())

def calendar_registry() -> CalendarResolverRegistry:
    return CalendarResolverRegistry(
        {
            "CAL@1": WorkingTimeResolver(WorkingCalendar()),
            "WEEKEND@1": WorkingTimeResolver(
                WorkingCalendar(working_weekdays=frozenset(range(7)))
            ),
        }
    )


def test_authoritative_batch_applies_activity_calendar_registry_to_schedule():
    base = snapshot("P1", date(2026, 10, 10))
    activity = Activity(id="P1-A", duration=2)
    weekend = CalendarReference("WEEKEND", "1")
    configured = replace(
        base,
        activities=(activity,),
        activity_calendar_assignments=(ActivityCalendarAssignment("P1-A", weekend),),
    )

    result = execute_authoritative_schedule_batch(
        [configured],
        resolvers={"P1": resolver()},
        calendar_registry=calendar_registry(),
    )

    scheduled = result.project("P1").result.early_activities["P1-A"]
    assert scheduled.finish == date(2026, 10, 2)


def test_duplicate_snapshot_id_is_rejected_before_graph_construction():
    first = snapshot("P1", date(2026, 10, 10))
    duplicate = AuthoritativeScheduleInput(
        snapshot_id=first.snapshot_id,
        tenant_id="tenant",
        project_id="P2",
        project_revision=1,
        project_leveling_priority=10,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL", "1"),
        activities=(Activity(id="P2-A", duration=1),),
        relationships=(),
        activity_calendar_assignments=(ActivityCalendarAssignment("P2-A", CalendarReference("CAL", "1")),),
        project_finish=date(2026, 10, 20),
        project_start=date(2026, 10, 1),
        schedule_options=ScheduleOptions(),
    )
    with pytest.raises(UnsupportedMultiProjectSchedulingError, match="DUPLICATE_SNAPSHOT_ID"):
        execute_authoritative_schedule_batch(
            [first, duplicate], resolvers={"P1": resolver(), "P2": resolver()}
        )


def test_mixed_tenants_are_rejected_before_graph_construction():
    first = snapshot("P1", date(2026, 10, 10))
    second = AuthoritativeScheduleInput(
        snapshot_id="s-P2",
        tenant_id="other-tenant",
        project_id="P2",
        project_revision=1,
        project_leveling_priority=10,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL", "1"),
        activities=(Activity(id="P2-A", duration=1),),
        relationships=(),
        activity_calendar_assignments=(ActivityCalendarAssignment("P2-A", CalendarReference("CAL", "1")),),
        project_finish=date(2026, 10, 20),
        project_start=date(2026, 10, 1),
        schedule_options=ScheduleOptions(),
    )
    with pytest.raises(UnsupportedMultiProjectSchedulingError, match="MULTI_PROJECT_CROSS_TENANT_NOT_SUPPORTED"):
        execute_authoritative_schedule_batch(
            [first, second], resolvers={"P1": resolver(), "P2": resolver()}
        )


def test_time_aware_snapshot_is_rejected_before_graph_construction():
    from datetime import datetime, timezone

    first = snapshot("P1", date(2026, 10, 10))
    reference = CalendarReference("TIME-CAL", "1", kind="working-time")
    context = SchedulingCalendarContext(project=reference, activity=reference)
    second = AuthoritativeScheduleInput(
        snapshot_id="s-P2",
        tenant_id="tenant",
        project_id="P2",
        project_revision=1,
        project_leveling_priority=10,
        mode=AuthoritativeScheduleMode.TIME_AWARE,
        project_calendar=reference,
        activities=(TimeActivity(id="P2-A", duration=TimeQuantity.working_hours(1), calendar_context=context),),
        relationships=(),
        activity_calendar_assignments=(ActivityCalendarAssignment("P2-A", reference),),
        project_finish=datetime(2026, 10, 20, tzinfo=timezone.utc),
        project_start=datetime(2026, 10, 1, tzinfo=timezone.utc),
        schedule_options=ScheduleOptions(),
    )
    with pytest.raises(UnsupportedMultiProjectSchedulingError, match="MULTI_PROJECT_TIME_AWARE_NOT_SUPPORTED"):
        execute_authoritative_schedule_batch(
            [first, second], resolvers={"P1": resolver(), "P2": resolver()}
        )
def test_batch_uses_each_project_finish_when_option_enabled():
    result = execute_authoritative_schedule_batch(
        [
            snapshot('P1', date(2026, 10, 10), options=ScheduleOptions(calculate_float_based_on_finish_date=True)),
            snapshot('P2', date(2026, 10, 20), options=ScheduleOptions(calculate_float_based_on_finish_date=True)),
        ],
        resolvers={'P1': resolver(), 'P2': resolver()},
    )
    assert result.project('P1').result.floats['P1-A'].total_float == 6
    assert result.project('P2').result.floats['P2-A'].total_float == 13


def test_authoritative_batch_uses_activity_calendar_context():
    p1 = replace(
        snapshot("P1", date(2026, 10, 10)),
        project_start=date(2026, 10, 2),
        activities=(Activity("P1-A", 2),),
        activity_calendar_assignments=(
            ActivityCalendarAssignment("P1-A", CalendarReference("WEEKEND", "1")),
        ),
    )
    p2 = replace(
        snapshot("P2", date(2026, 10, 10)),
        project_start=date(2026, 10, 2),
        activities=(Activity("P2-A", 2),),
    )
    result = execute_authoritative_schedule_batch(
        [p1, p2],
        resolvers={"P1": resolver(), "P2": resolver()},
        calendar_registry=calendar_registry(),
    )

    assert result.project("P1").result.activities["P1-A"].finish == date(2026, 10, 3)
    assert result.project("P2").result.activities["P2-A"].finish == date(2026, 10, 5)


def test_authoritative_batch_uses_activity_calendar_context_for_shared_graph():
    p1 = replace(
        snapshot("P1", date(2026, 10, 10)),
        project_start=date(2026, 10, 1),
        activities=(Activity("P1-A", 1),),
    )
    p2 = replace(
        snapshot("P2", date(2026, 10, 10)),
        project_start=date(2026, 10, 1),
        activities=(Activity("P2-A", 1),),
        activity_calendar_assignments=(
            ActivityCalendarAssignment("P2-A", CalendarReference("WEEKEND", "1")),
        ),
        constraints=(
            ActivityConstraint(
                "P2-A",
                ConstraintType.START_NO_EARLIER_THAN,
                date(2026, 10, 3),
            ),
        ),
    )
    result = execute_authoritative_schedule_batch(
        [p1, p2],
        resolvers={"P1": resolver(), "P2": resolver()},
        calendar_registry=calendar_registry(),
        external_relationships=(Relationship("P1-A", "P2-A"),),
        activity_project_ids={"P1-A": "P1", "P2-A": "P2"},
    )

    assert result.project("P1").result.activities["P1-A"].finish == date(2026, 10, 1)
    # FS lag stays on the separate relationship-lag calendar (Mon-Fri).
    # The successor's WEEKEND activity calendar normalizes the constraint
    # target to Saturday, Oct 3.
    assert result.project("P2").result.activities["P2-A"].start == date(2026, 10, 3)
    assert result.project("P2").result.activities["P2-A"].finish == date(2026, 10, 3)


def test_mixed_activity_calendars_are_rejected_for_shared_resource_leveling():
    p1 = replace(
        snapshot("P1", date(2026, 10, 10)),
        activity_calendar_assignments=(
            ActivityCalendarAssignment("P1-A", CalendarReference("WEEKEND", "1")),
        ),
    )
    p2 = snapshot("P2", date(2026, 10, 10))
    leveling_input = SchedulerLevelingInput(
        forward_activities=(),
        backward_activities=(),
        capacities=(),
        options=ResourceLevelingOptions(level_all_resources=True),
    )

    with pytest.raises(
        UnsupportedMultiProjectSchedulingError,
        match="MULTI_PROJECT_RESOURCE_LEVELING_ACTIVITY_CALENDARS_NOT_SUPPORTED",
    ):
        execute_authoritative_schedule_batch(
            [p1, p2],
            resolvers={"P1": resolver(), "P2": resolver()},
            leveling_input=leveling_input,
            calendar_registry=calendar_registry(),
        )


def test_batch_uses_latest_finish_when_option_disabled():
    result = execute_authoritative_schedule_batch(
        [
            snapshot('P1', date(2026, 10, 10)),
            snapshot('P2', date(2026, 10, 20)),
        ],
        resolvers={'P1': resolver(), 'P2': resolver()},
    )
    assert result.batch.finish_boundary_for('P1') == date(2026, 10, 20)
    assert result.project('P1').result.floats['P1-A'].total_float == 13


def test_mixed_float_basis_is_explicitly_unsupported():
    with pytest.raises(
        UnsupportedMultiProjectSchedulingError,
        match='mixed calculate_float_based_on_finish_date settings',
    ):
        execute_authoritative_schedule_batch(
            [
                snapshot(
                    'P1',
                    date(2026, 10, 10),
                    options=ScheduleOptions(calculate_float_based_on_finish_date=True),
                ),
                snapshot(
                    'P2',
                    date(2026, 10, 20),
                    options=ScheduleOptions(calculate_float_based_on_finish_date=False),
                ),
            ],
            resolvers={'P1': resolver(), 'P2': resolver()},
        )


def test_cross_project_relationship_executes_through_shared_batch_graph():
    relationship = Relationship('P1-A', 'P2-A')
    result = execute_authoritative_schedule_batch(
        [
            snapshot('P1', date(2026, 10, 10)),
            snapshot('P2', date(2026, 10, 20)),
        ],
        resolvers={'P1': resolver(), 'P2': resolver()},
        external_relationships=(relationship,),
        activity_project_ids={'P1-A': 'P1', 'P2-A': 'P2'},
    )
    p1_result = result.project('P1').result
    p2_result = result.project('P2').result
    p1 = p1_result.activities['P1-A']
    p2 = p2_result.activities['P2-A']
    assert p2.start > p1.finish
    assert set(p1_result.early_activities or {}) == {'P1-A'}
    assert set(p1_result.late_activities or {}) == {'P1-A'}
    assert set(p2_result.early_activities or {}) == {'P2-A'}
    assert set(p2_result.late_activities or {}) == {'P2-A'}


def test_mixed_external_relationship_options_fail_fast():
    with pytest.raises(
        UnsupportedMultiProjectSchedulingError,
        match="MULTI_PROJECT_RELATIONSHIP_OPTION_MISMATCH",
    ):
        execute_authoritative_schedule_batch(
            [
                snapshot(
                    "P1",
                    date(2026, 10, 10),
                    options=ScheduleOptions(ignore_other_project_relationships=True),
                ),
                snapshot(
                    "P2",
                    date(2026, 10, 20),
                    options=ScheduleOptions(ignore_other_project_relationships=False),
                ),
            ],
            resolvers={"P1": resolver(), "P2": resolver()},
            external_relationships=(Relationship("P1-A", "P2-A"),),
        )


def test_cross_project_relationship_is_ignored_when_option_enabled():
    options = ScheduleOptions(ignore_other_project_relationships=True)
    result = execute_authoritative_schedule_batch(
        [
            snapshot('P1', date(2026, 10, 10), options=options),
            snapshot('P2', date(2026, 10, 20), options=options),
        ],
        resolvers={'P1': resolver(), 'P2': resolver()},
        external_relationships=(Relationship('P1-A', 'P2-A'),),
        activity_project_ids={'P1-A': 'P1', 'P2-A': 'P2'},
    )
    assert len(result.projects) == 2


def assignment(project_id, resource_id):
    return ExternalResourceAssignment(
        project_id=project_id,
        resource_id=resource_id,
        period=date(2026, 10, 1),
        units=Decimal('1'),
        activity_id=f'{project_id}-A',
    )


@pytest.mark.parametrize(
    ('external_priority', 'expected_external'),
    [(4, True), (5, True), (6, False)],
)
def test_external_resource_assignment_priority_limit_boundary(
    external_priority, expected_external
):
    options = ScheduleOptions(include_external_res_ass=True, external_project_priority_limit=5)
    result = execute_authoritative_schedule_batch(
        [
            snapshot('P1', date(2026, 10, 10), options=options, priority=10),
            snapshot('P2', date(2026, 10, 20), priority=external_priority),
        ],
        resolvers={'P1': resolver(), 'P2': resolver()},
        resource_assignments=(assignment('P1', 'R1'), assignment('P2', 'R2')),
    )
    resource_ids = [d.resource_id for d in result.project('P1').resource_demands]
    assert ('R2' in resource_ids) is expected_external


def test_external_resource_assignment_is_excluded_when_option_disabled():
    options = ScheduleOptions(include_external_res_ass=False, external_project_priority_limit=5)
    result = execute_authoritative_schedule_batch(
        [
            snapshot('P1', date(2026, 10, 10), options=options, priority=10),
            snapshot('P2', date(2026, 10, 20), priority=1),
        ],
        resolvers={'P1': resolver(), 'P2': resolver()},
        resource_assignments=(assignment('P1', 'R1'), assignment('P2', 'R2')),
    )
    assert [d.resource_id for d in result.project('P1').resource_demands] == []


def test_single_project_preserves_existing_behavior_with_multi_project_options_disabled():
    result = execute_authoritative_schedule_batch(
        [snapshot('P1', date(2026, 10, 10))],
        resolvers={'P1': resolver()},
    )
    assert result.project('P1').result.project_finish == date(2026, 10, 9)


def test_combined_external_boundary_options_are_deterministic():
    options = ScheduleOptions(
        calculate_float_based_on_finish_date=False,
        ignore_other_project_relationships=True,
        include_external_res_ass=True,
        external_project_priority_limit=5,
    )
    kwargs = dict(
        resolvers={'P1': resolver(), 'P2': resolver()},
        external_relationships=(Relationship('P1-A', 'P2-A'),),
        activity_project_ids={'P1-A': 'P1', 'P2-A': 'P2'},
        resource_assignments=(assignment('P1', 'R1'), assignment('P2', 'R2')),
    )
    first = execute_authoritative_schedule_batch(
        [
            snapshot('P1', date(2026, 10, 10), options=options),
            snapshot('P2', date(2026, 10, 20), options=options, priority=5),
        ],
        **kwargs,
    )
    second = execute_authoritative_schedule_batch(
        [
            snapshot('P1', date(2026, 10, 10), options=options),
            snapshot('P2', date(2026, 10, 20), options=options, priority=5),
        ],
        **kwargs,
    )
    assert first.project('P1').result == second.project('P1').result
    assert first.project('P1').resource_demands == second.project('P1').resource_demands
    assert first.batch.finish_boundary_for('P1') == date(2026, 10, 20)
    assert first.project('P1').result.floats['P1-A'].total_float == 13
    assert [d.resource_id for d in first.project('P1').resource_demands] == ['R1', 'R2']


def test_unsupported_multi_project_resource_leveling_never_silently_falls_back():
    with pytest.raises(ValueError, match='unsupported schedule options') as exc:
        execute_authoritative_schedule_batch(
            [snapshot('P1', date(2026, 10, 10), options=ScheduleOptions(level_all_resources=True))],
            resolvers={'P1': resolver()},
        )
    assert 'level_all_resources' in str(exc.value)


def test_missing_external_project_membership_is_explicit():
    with pytest.raises(ValueError, match='MISSING_PROJECT_ID_FOR_RELATIONSHIP_ENDPOINT'):
        execute_authoritative_schedule_batch(
            [snapshot('P1', date(2026, 10, 10), options=ScheduleOptions(ignore_other_project_relationships=True))],
            resolvers={'P1': resolver()},
            external_relationships=(Relationship('P1-A', 'UNKNOWN-A'),),
        )


def test_shared_resource_leveling_runs_once_for_the_batch_graph():
    options = ScheduleOptions(
        level_all_resources=True,
        include_external_res_ass=False,
        calculate_float_based_on_finish_date=False,
    )
    leveling_options = ResourceLevelingOptions(level_all_resources=True)
    demand_p1 = ResourceDemand("R1", date(2026, 10, 1), Decimal("1"), "P1-A")
    demand_p2 = ResourceDemand("R1", date(2026, 10, 1), Decimal("1"), "P2-A")
    forward = (
        LevelingActivity("P1-A", date(2026, 10, 1), date(2026, 10, 1), 10, (demand_p1,)),
        LevelingActivity("P2-A", date(2026, 10, 1), date(2026, 10, 1), 10, (demand_p2,)),
    )
    backward = (
        BackwardLevelingActivity("P1-A", date(2026, 10, 1), date(2026, 10, 1), date(2026, 10, 10), date(2026, 10, 10), (demand_p1,)),
        BackwardLevelingActivity("P2-A", date(2026, 10, 1), date(2026, 10, 1), date(2026, 10, 10), date(2026, 10, 10), (demand_p2,)),
    )
    leveling_input = SchedulerLevelingInput(
        forward_activities=forward,
        backward_activities=backward,
        capacities=(
            ResourceCapacity("R1", date(2026, 10, 1), Decimal("1")),
            ResourceCapacity("R1", date(2026, 10, 2), Decimal("1")),
        ),
        options=leveling_options,
    )
    result = execute_authoritative_schedule_batch(
        [
            snapshot("P1", date(2026, 10, 10), options=options),
            snapshot("P2", date(2026, 10, 10), options=options),
        ],
        resolvers={"P1": resolver(), "P2": resolver()},
        leveling_input=leveling_input,
    )
    p1 = result.project("P1").result.activities["P1-A"]
    p2 = result.project("P2").result.activities["P2-A"]
    assert p1.finish < p2.start or p2.finish < p1.start


@pytest.mark.parametrize(
    "changed_option",
    [
        {"critical_activity_float_threshold": 1.0},
        {"make_open_ended_activities_critical": True},
        {"multiple_float_paths_enabled": True},
        {"maximum_multiple_float_paths": 3},
        {"use_expected_finish_dates": True},
        {"data_date": date(2026, 10, 2)},
    ],
)
def test_shared_graph_rejects_calculation_option_mismatch_independent_of_order(
    changed_option,
):
    first = snapshot("P1", date(2026, 10, 10))
    second = snapshot("P2", date(2026, 10, 20), options=ScheduleOptions(**changed_option))
    edge = Relationship("P1-A", "P2-A")

    errors = []
    for ordered in ((first, second), (second, first)):
        with pytest.raises(
            UnsupportedMultiProjectSchedulingError,
            match="MULTI_PROJECT_SCHEDULE_OPTIONS_MISMATCH:",
        ) as exc:
            execute_authoritative_schedule_batch(
                ordered,
                resolvers={"P1": resolver(), "P2": resolver()},
                external_relationships=(edge,),
            )
        errors.append(str(exc.value))

    assert errors[0] == errors[1]
    assert errors[0].endswith(",".join(sorted(changed_option)))


def test_shared_graph_allows_project_routing_options_to_differ_when_not_used_globally():
    first = snapshot(
        "P1",
        date(2026, 10, 10),
        options=ScheduleOptions(include_external_res_ass=False),
    )
    second = snapshot(
        "P2",
        date(2026, 10, 20),
        options=ScheduleOptions(include_external_res_ass=True),
    )

    result = execute_authoritative_schedule_batch(
        (first, second),
        resolvers={"P1": resolver(), "P2": resolver()},
        external_relationships=(Relationship("P1-A", "P2-A"),),
    )

    assert {item.project_id for item in result.projects} == {"P1", "P2"}
