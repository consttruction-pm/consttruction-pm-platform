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


@pytest.fixture
def resolver():
    return WorkingTimeResolver(WorkingCalendar())


def test_start_no_earlier_than_constraint():
    resolver = WorkingTimeResolver(WorkingCalendar())
    result = forward_pass(
        [Activity("A", 1)],
        [],
        date(2026, 9, 21),
        resolver,
        [ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 23))],
    )
    assert result["A"].start == date(2026, 9, 23)


def test_finish_no_earlier_than_constraint():
    resolver = WorkingTimeResolver(WorkingCalendar())
    result = forward_pass(
        [Activity("A", 1)],
        [],
        date(2026, 9, 21),
        resolver,
        [ActivityConstraint("A", ConstraintType.FINISH_NO_EARLIER_THAN, date(2026, 9, 23))],
    )
    assert result["A"].finish == date(2026, 9, 23)


def test_start_no_later_than_violation():
    resolver = WorkingTimeResolver(WorkingCalendar())
    with pytest.raises(ConstraintViolation):
        forward_pass(
            [Activity("A", 1)],
            [],
            date(2026, 9, 23),
            resolver,
            [ActivityConstraint("A", ConstraintType.START_NO_LATER_THAN, date(2026, 9, 22))],
        )


def test_mandatory_start_is_enforced():
    resolver = WorkingTimeResolver(WorkingCalendar())
    result = forward_pass(
        [Activity("A", 1)],
        [],
        date(2026, 9, 21),
        resolver,
        [ActivityConstraint("A", ConstraintType.MANDATORY_START, date(2026, 9, 23))],
    )
    assert result["A"].start == date(2026, 9, 23)


def test_constraint_rejects_unknown_activity():
    resolver = WorkingTimeResolver(WorkingCalendar())
    with pytest.raises(ValueError):
        forward_pass(
            [Activity("A", 1)],
            [],
            date(2026, 9, 21),
            resolver,
            [ActivityConstraint("B", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 22))],
        )
