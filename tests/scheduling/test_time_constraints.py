from datetime import datetime, time

import pytest

from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry, SchedulingCalendarContext
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_calendar import TimeAwareWorkingTimeResolver, WorkingTimeCalendar
from construction_pm.scheduling.time_constraints import TimeActivityConstraint, TimeConstraintType, TimeConstraintViolation
from construction_pm.scheduling.time_duration import LagQuantity, TimeQuantity
from construction_pm.scheduling.time_forward_pass import TimeActivity, TimeRelationship
from construction_pm.scheduling.time_schedule import time_schedule


def registry():
    calendar = WorkingTimeCalendar(
        daily_intervals={
            0: ((time(8), time(12)), (time(13), time(17))),
            1: ((time(8), time(12)), (time(13), time(17))),
            2: ((time(8), time(12)), (time(13), time(17))),
            3: ((time(8), time(12)), (time(13), time(17))),
            4: ((time(8), time(12)), (time(13), time(17))),
        }
    )
    return CalendarResolverRegistry(time_resolvers={"site@1": TimeAwareWorkingTimeResolver(calendar)})


def context():
    ref = CalendarReference("site", "1", "working-time")
    return SchedulingCalendarContext(project=ref, activity=ref, relationship_lag=ref)


def test_start_no_earlier_than_moves_early_date_but_does_not_shift_late_date():
    ctx = context()
    activities = [TimeActivity("A", TimeQuantity.working_hours(2), ctx)]
    result = time_schedule(
        activities, [], datetime(2026, 9, 22, 8), datetime(2026, 9, 22, 17), registry(),
        [TimeActivityConstraint("A", TimeConstraintType.START_NO_EARLIER_THAN, datetime(2026, 9, 22, 13))]
    )
    assert result.early_activities["A"].start == datetime(2026, 9, 22, 13)
    assert result.late_activities["A"].start == datetime(2026, 9, 22, 15)


def test_finish_no_later_than_reduces_latest_date():
    ctx = context()
    activities = [TimeActivity("A", TimeQuantity.working_hours(2), ctx)]
    result = time_schedule(
        activities, [], datetime(2026, 9, 22, 8), datetime(2026, 9, 22, 17), registry(),
        [TimeActivityConstraint("A", TimeConstraintType.FINISH_NO_LATER_THAN, datetime(2026, 9, 22, 15))]
    )
    assert result.late_activities["A"].finish == datetime(2026, 9, 22, 15)


def test_mandatory_start_must_not_conflict_with_predecessor_logic():
    ctx = context()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(2), ctx),
        TimeActivity("B", TimeQuantity.working_hours(2), ctx),
    ]
    relationships = [TimeRelationship("A", "B", RelationshipType.FS)]
    constraints = [TimeActivityConstraint("B", TimeConstraintType.MANDATORY_START, datetime(2026, 9, 22, 8))]
    with pytest.raises(TimeConstraintViolation):
        time_schedule(activities, relationships, datetime(2026, 9, 22, 8), datetime(2026, 9, 22, 17), registry(), constraints)


def test_mandatory_finish_is_exact_on_both_early_and_late_paths_when_feasible():
    ctx = context()
    activities = [TimeActivity("A", TimeQuantity.working_hours(2), ctx)]
    constraints = [TimeActivityConstraint("A", TimeConstraintType.MANDATORY_FINISH, datetime(2026, 9, 22, 10))]
    result = time_schedule(
        activities, [], datetime(2026, 9, 22, 8), datetime(2026, 9, 22, 10), registry(), constraints
    )
    assert result.early_activities["A"].finish == datetime(2026, 9, 22, 10)
    assert result.late_activities["A"].finish == datetime(2026, 9, 22, 10)
