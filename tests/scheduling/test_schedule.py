from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.forward_pass import forward_pass
from construction_pm.scheduling.schedule import backward_pass, schedule


@pytest.fixture
def resolver():
    return WorkingTimeResolver(WorkingCalendar())


def test_backward_pass_produces_zero_float_on_critical_chain(resolver):
    activities = [Activity("A", 2), Activity("B", 2), Activity("C", 1)]
    relationships = [
        __import__("construction_pm.scheduling.relationships", fromlist=["Relationship"]).Relationship("A", "B"),
        __import__("construction_pm.scheduling.relationships", fromlist=["Relationship"]).Relationship("B", "C"),
    ]
    early = forward_pass(activities, relationships, date(2026, 9, 21), resolver)
    late = backward_pass(activities, relationships, early, None, resolver)

    assert late["C"].start == date(2026, 9, 24)
    assert late["B"].start == date(2026, 9, 22)
    assert late["A"].start == date(2026, 9, 21)


def test_schedule_calculates_total_and_free_float(resolver):
    from construction_pm.scheduling.relationships import Relationship

    activities = [Activity("A", 1), Activity("B", 1), Activity("C", 1)]
    relationships = [
        Relationship("A", "C"),
        Relationship("B", "C"),
    ]
    result = schedule(activities, relationships, date(2026, 9, 21), resolver)

    assert result.floats["C"].total_float == 0
    assert result.floats["A"].total_float == 1
    assert result.floats["A"].free_float == 1
    assert result.floats["A"].critical is False
    assert result.floats["B"].total_float == 1
    assert result.floats["B"].free_float == 1


def test_backward_pass_uses_explicit_project_finish(resolver):
    from construction_pm.scheduling.relationships import Relationship

    activities = [Activity("A", 1)]
    early = forward_pass(activities, [], date(2026, 9, 21), resolver)
    late = backward_pass(
        activities, [], early, date(2026, 9, 23), resolver
    )
    assert late["A"].start == date(2026, 9, 23)


def test_backward_pass_rejects_missing_activity(resolver):
    from construction_pm.scheduling.relationships import Relationship

    activities = [Activity("A", 1)]
    with pytest.raises(ValueError):
        backward_pass(
            activities,
            [],
            {},
            None,
            resolver,
        )
