from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.constraints import ActivityConstraint, ConstraintType
from construction_pm.scheduling.forward_pass import forward_pass
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.schedule import ScheduleMode, ScheduleOptions, _relationship_holds, schedule


@pytest.fixture
def resolver():
    return WorkingTimeResolver(WorkingCalendar())


@pytest.mark.parametrize("relationship_type", list(RelationshipType))
@pytest.mark.parametrize("lag", [-2, -1, 0, 1, 2])
def test_all_relationship_types_and_lags_are_calendar_feasible(resolver, relationship_type, lag):
    activities = [Activity("A", 2), Activity("B", 3)]
    relationship = Relationship("A", "B", relationship_type, lag=lag)
    result = schedule(activities, [relationship], date(2026, 9, 21), resolver)
    assert _relationship_holds(
        relationship, result.early_activities["A"], result.early_activities["B"], resolver
    )
    assert _relationship_holds(
        relationship, result.late_activities["A"], result.late_activities["B"], resolver
    )


def test_schedule_is_deterministic_when_activity_and_relationship_input_order_changes(resolver):
    activities_a = [Activity("C", 1), Activity("A", 2), Activity("B", 1)]
    relationships_a = [
        Relationship("B", "C", RelationshipType.FS, lag=1),
        Relationship("A", "B", RelationshipType.SS, lag=-1),
    ]
    activities_b = list(reversed(activities_a))
    relationships_b = list(reversed(relationships_a))

    first = schedule(activities_a, relationships_a, date(2026, 9, 21), resolver)
    second = schedule(activities_b, relationships_b, date(2026, 9, 21), resolver)

    assert first.early_activities == second.early_activities
    assert first.late_activities == second.late_activities
    assert first.floats == second.floats


def test_holiday_and_weekend_boundaries_are_reproducible(resolver):
    holiday = date(2026, 9, 23)
    resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({holiday}))
    )
    activities = [Activity("A", 2), Activity("B", 1)]
    relationship = Relationship("A", "B", RelationshipType.FS, lag=1)

    result = schedule(activities, [relationship], date(2026, 9, 21), resolver)

    assert result.early_activities["A"].start == date(2026, 9, 21)
    assert result.early_activities["A"].finish == date(2026, 9, 22)
    assert result.early_activities["B"].start == date(2026, 9, 24)


def test_lower_bound_constraint_can_reduce_float_without_moving_late_date(resolver):
    result = schedule(
        [Activity("A", 1)],
        [],
        date(2026, 9, 21),
        resolver,
        project_finish=date(2026, 9, 25),
        constraints=[
            ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 24))
        ],
    )
    assert result.early_activities["A"].start == date(2026, 9, 24)
    assert result.late_activities["A"].start == date(2026, 9, 25)
    assert result.floats["A"].total_float == 1


def test_upper_bound_constraint_is_respected_by_late_schedule(resolver):
    result = schedule(
        [Activity("A", 1)],
        [],
        date(2026, 9, 21),
        resolver,
        project_finish=date(2026, 9, 25),
        constraints=[
            ActivityConstraint("A", ConstraintType.START_NO_LATER_THAN, date(2026, 9, 23))
        ],
    )
    assert result.early_activities["A"].start == date(2026, 9, 21)
    assert result.late_activities["A"].start == date(2026, 9, 23)


def test_earliest_and_alap_are_distinct_outputs_but_share_the_same_float_analysis(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1)]
    relationships = [Relationship("A", "C"), Relationship("B", "C")]

    earliest = schedule(activities, relationships, date(2026, 9, 21), resolver)
    alap = schedule(
        activities,
        relationships,
        date(2026, 9, 21),
        resolver,
        options=ScheduleOptions(ScheduleMode.ALAP),
    )

    assert earliest.activities == earliest.early_activities
    assert alap.activities == alap.late_activities
    assert earliest.floats == alap.floats


def test_zero_duration_is_normalized_without_breaking_network_semantics(resolver):
    activities = [Activity("A", 0), Activity("B", 1)]
    relationship = Relationship("A", "B", RelationshipType.FS)
    result = schedule(activities, [relationship], date(2026, 9, 21), resolver)

    assert result.early_activities["A"].start == result.early_activities["A"].finish
    assert result.early_activities["B"].start == date(2026, 9, 22)


def test_custom_six_day_calendar_is_shared_by_scheduling_core(resolver):
    calendar = WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4, 5}))
    resolver = WorkingTimeResolver(calendar)
    result = schedule(
        [Activity("A", 2), Activity("B", 1)],
        [Relationship("A", "B", RelationshipType.FS)],
        date(2026, 9, 25),
        resolver,
    )
    assert result.early_activities["A"].finish == date(2026, 9, 26)
    assert result.early_activities["B"].start == date(2026, 9, 28)
