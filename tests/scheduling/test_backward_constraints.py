from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.constraints import (
    ActivityConstraint,
    ConstraintType,
    ConstraintViolation,
)
from construction_pm.scheduling.forward_pass import forward_pass
from construction_pm.scheduling.relationships import Relationship
from construction_pm.scheduling.schedule import backward_pass, schedule


@pytest.fixture
def resolver():
    return WorkingTimeResolver(WorkingCalendar())


def test_backward_start_no_later_than_caps_late_start(resolver):
    activities = [Activity("A", 1)]
    early = forward_pass(activities, [], date(2026, 9, 21), resolver)
    late = backward_pass(
        activities, [], early, date(2026, 9, 25), resolver,
        [ActivityConstraint("A", ConstraintType.START_NO_LATER_THAN, date(2026, 9, 23))],
    )
    assert late["A"].start == date(2026, 9, 23)


def test_backward_finish_no_later_than_caps_late_finish(resolver):
    activities = [Activity("A", 2)]
    early = forward_pass(activities, [], date(2026, 9, 21), resolver)
    late = backward_pass(
        activities, [], early, date(2026, 9, 28), resolver,
        [ActivityConstraint("A", ConstraintType.FINISH_NO_LATER_THAN, date(2026, 9, 24))],
    )
    assert late["A"].finish == date(2026, 9, 24)
    assert late["A"].start == date(2026, 9, 23)


def test_schedule_accepts_consistent_mandatory_finish(resolver):
    activities = [Activity("A", 1)]
    constraints = [
        ActivityConstraint("A", ConstraintType.MANDATORY_FINISH, date(2026, 9, 23))
    ]
    result = schedule(
        activities, [], date(2026, 9, 21), resolver, constraints=constraints
    )
    assert result.activities["A"].finish == date(2026, 9, 23)
    assert result.floats["A"].critical is True


def test_backward_rejects_unknown_constraint_activity(resolver):
    activities = [Activity("A", 1)]
    early = forward_pass(activities, [], date(2026, 9, 21), resolver)
    with pytest.raises(ValueError):
        backward_pass(
            activities, [], early, None, resolver,
            [ActivityConstraint("B", ConstraintType.START_NO_LATER_THAN, date(2026, 9, 22))],
        )
