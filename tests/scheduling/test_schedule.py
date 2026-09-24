from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.forward_pass import forward_pass
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.constraints import ActivityConstraint, ConstraintType
from construction_pm.scheduling.schedule import (
    ScheduleMode,
    ScheduleOptions,
    _relationship_holds,
    backward_pass,
    schedule,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver


def _working_float_days(start, finish, resolver):
    return resolver.working_days_between(start, finish)


@pytest.fixture
def resolver():
    return WorkingTimeResolver(WorkingCalendar())


def test_backward_pass_produces_zero_float_on_critical_chain(resolver):
    activities = [Activity("A", 2), Activity("B", 2), Activity("C", 1)]
    relationships = [Relationship("A", "B"), Relationship("B", "C")]
    early = forward_pass(activities, relationships, date(2026, 9, 21), resolver)
    late = backward_pass(activities, relationships, early, None, resolver)

    assert late["C"].start == date(2026, 9, 25)
    assert late["B"].start == date(2026, 9, 23)
    assert late["A"].start == date(2026, 9, 21)


def test_backward_pass_propagates_successor_late_dates_in_branching_network(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 3), Activity("D", 1)]
    relationships = [
        Relationship("A", "C", RelationshipType.FS),
        Relationship("B", "D", RelationshipType.FS),
        Relationship("C", "D", RelationshipType.FS),
    ]
    early = forward_pass(activities, relationships, date(2026, 9, 21), resolver)
    late = backward_pass(activities, relationships, early, None, resolver)

    assert early["D"].finish == date(2026, 9, 25)
    assert late["D"].start == date(2026, 9, 25)
    assert late["C"].start == date(2026, 9, 22)
    assert late["A"].start == date(2026, 9, 22)
    assert late["B"].start == date(2026, 9, 25)


def test_backward_pass_rejects_project_finish_before_early_finish(resolver):
    activities = [Activity("A", 2)]
    early = forward_pass(activities, [], date(2026, 9, 21), resolver)

    with pytest.raises(ValueError):
        backward_pass(activities, [], early, date(2026, 9, 21), resolver)


def test_schedule_calculates_total_and_free_float(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1)]
    relationships = [Relationship("A", "C"), Relationship("B", "C")]
    result = schedule(activities, relationships, date(2026, 9, 21), resolver)

    assert result.floats["C"].total_float == 0
    assert result.floats["A"].total_float == 1
    assert result.floats["A"].free_float == 1
    assert result.floats["A"].critical is False
    assert result.floats["B"].total_float == 1
    assert result.floats["B"].free_float == 1


def test_backward_pass_uses_explicit_project_finish(resolver):
    activities = [Activity("A", 1)]
    early = forward_pass(activities, [], date(2026, 9, 21), resolver)
    late = backward_pass(activities, [], early, date(2026, 9, 23), resolver)
    assert late["A"].start == date(2026, 9, 23)


def test_backward_pass_rejects_missing_activity(resolver):
    activities = [Activity("A", 1)]
    with pytest.raises(ValueError):
        backward_pass(activities, [], {}, None, resolver)


@pytest.mark.parametrize(
    ("relationship_type", "lag"),
    [
        (RelationshipType.FS, 1),
        (RelationshipType.FS, -1),
        (RelationshipType.SS, 1),
        (RelationshipType.SS, -1),
        (RelationshipType.FF, 1),
        (RelationshipType.FF, -1),
        (RelationshipType.SF, 1),
        (RelationshipType.SF, -1),
    ],
)
def test_backward_pass_lagged_result_satisfies_relationship_semantics(
    resolver, relationship_type, lag
):
    activities = [Activity("A", 2), Activity("B", 2)]
    relationship = Relationship("A", "B", relationship_type, lag=lag)
    early = forward_pass(activities, [relationship], date(2026, 9, 21), resolver)
    late = backward_pass(activities, [relationship], early, None, resolver)

    assert _relationship_holds(
        relationship, late["A"], late["B"], resolver
    )
    assert late["A"].start <= late["A"].finish
    assert late["B"].start <= late["B"].finish


@pytest.mark.parametrize("relationship_type", list(RelationshipType))
def test_backward_pass_relationship_lag_with_holiday_remains_feasible(
    resolver, relationship_type
):
    holiday = date(2026, 9, 22)
    resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({holiday}))
    )
    activities = [Activity("A", 2), Activity("B", 2)]
    relationship = Relationship("A", "B", relationship_type, lag=1)
    early = forward_pass(activities, [relationship], date(2026, 9, 21), resolver)
    late = backward_pass(activities, [relationship], early, None, resolver)

    assert _relationship_holds(
        relationship, late["A"], late["B"], resolver
    )


def test_alap_mode_selects_late_schedule_but_preserves_early_and_float_analysis(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1)]
    relationships = [Relationship("A", "C"), Relationship("B", "C")]

    result = schedule(
        activities,
        relationships,
        date(2026, 9, 21),
        resolver,
        options=ScheduleOptions(ScheduleMode.ALAP),
    )

    assert result.mode is ScheduleMode.ALAP
    assert result.activities["A"].start == date(2026, 9, 22)
    assert result.activities["B"].start == date(2026, 9, 22)
    assert result.activities["C"].start == date(2026, 9, 23)
    assert result.early_activities["A"].start == date(2026, 9, 21)
    assert result.late_activities["A"].start == date(2026, 9, 22)
    assert result.floats["A"].total_float == 1


def test_earliest_mode_remains_default_selected_schedule(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1)]
    relationships = [Relationship("A", "C"), Relationship("B", "C")]

    result = schedule(activities, relationships, date(2026, 9, 21), resolver)

    assert result.mode is ScheduleMode.EARLIEST
    assert result.activities["A"].start == date(2026, 9, 21)
    assert result.early_activities["A"].start == date(2026, 9, 21)
    assert result.late_activities["A"].start == date(2026, 9, 22)



def test_constraint_reconciliation_preserves_nonnegative_float_and_criticality(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1)]
    relationships = [Relationship("A", "C"), Relationship("B", "C")]
    result = schedule(
        activities, relationships, date(2026, 9, 21), resolver,
        project_finish=date(2026, 9, 24),
        constraints=[
            ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 22))
        ],
    )
    assert result.floats["C"].total_float == 0
    assert result.floats["A"].total_float >= 0
    assert result.floats["B"].total_float >= 0
    assert result.floats["C"].critical is True
    assert result.floats["A"].critical is False


def test_constrained_alap_preserves_early_late_and_selected_schedule(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1)]
    relationships = [Relationship("A", "C"), Relationship("B", "C")]
    result = schedule(
        activities, relationships, date(2026, 9, 21), resolver,
        project_finish=date(2026, 9, 25),
        constraints=[
            ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 22))
        ],
        options=ScheduleOptions(ScheduleMode.ALAP),
    )
    assert result.activities["A"].start == result.late_activities["A"].start
    assert result.activities["A"].start >= result.early_activities["A"].start
    assert result.late_activities["A"].start >= date(2026, 9, 22)
    assert result.floats["A"].total_float >= 0


def test_calendar_holiday_constraint_reconciliation_preserves_float(resolver):
    holiday = date(2026, 9, 22)
    resolver = WorkingTimeResolver(WorkingCalendar(holidays=frozenset({holiday})))
    activities = [Activity("A", 1), Activity("B", 1)]
    relationships = [Relationship("A", "B", RelationshipType.FS, lag=1)]
    result = schedule(
        activities, relationships, date(2026, 9, 21), resolver,
        project_finish=date(2026, 9, 29),
        constraints=[
            ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, holiday)
        ],
    )
    assert result.early_activities["A"].start > holiday
    assert result.floats["A"].total_float >= 0
    assert result.floats["B"].total_float >= 0


@pytest.mark.parametrize("relationship_type", list(RelationshipType))
@pytest.mark.parametrize("mode", [ScheduleMode.EARLIEST, ScheduleMode.ALAP])
def test_schedule_mode_preserves_constraints_and_relationships(resolver, relationship_type, mode):
    activities = [Activity("A", 1), Activity("B", 1)]
    relationship = Relationship("A", "B", relationship_type, lag=1)
    result = schedule(
        activities,
        [relationship],
        date(2026, 9, 21),
        resolver,
        project_finish=date(2026, 9, 30),
        constraints=[ActivityConstraint("B", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 24))],
        options=ScheduleOptions(mode),
    )
    selected = result.activities
    assert selected["B"].start >= date(2026, 9, 24)
    assert _relationship_holds(relationship, selected["A"], selected["B"], resolver)
    assert result.mode is mode
    assert result.early_activities["B"].start >= date(2026, 9, 24)
    assert result.late_activities["B"].start >= date(2026, 9, 24)
    assert result.floats["A"].total_float >= 0
    assert result.floats["B"].total_float >= 0


def test_alap_does_not_mutate_early_schedule_when_constraint_moves_late_schedule(resolver):
    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1)]
    relationships = [Relationship("A", "C"), Relationship("B", "C")]
    result = schedule(
        activities, relationships, date(2026, 9, 21), resolver,
        project_finish=date(2026, 9, 25),
        constraints=[ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 23))],
        options=ScheduleOptions(ScheduleMode.ALAP),
    )
    assert result.early_activities["A"].start == date(2026, 9, 23)
    assert result.activities["A"].start == result.late_activities["A"].start
    assert result.early_activities["A"].start <= result.late_activities["A"].start
    assert result.floats["A"].total_float == _working_float_days(
        result.early_activities["A"].start, result.late_activities["A"].start, resolver
    )
