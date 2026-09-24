from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.forward_pass import forward_pass
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.schedule import (
    ScheduleMode,
    ScheduleOptions,
    backward_pass,
    schedule,
)


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
    activities = [
        Activity("A", 1),
        Activity("B", 1),
        Activity("C", 3),
        Activity("D", 1),
    ]
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
