from datetime import datetime, time
from decimal import Decimal

from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
    SchedulingCalendarContext,
)
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_calendar import TimeAwareWorkingTimeResolver, WorkingTimeCalendar
from construction_pm.scheduling.time_duration import LagQuantity, TimeQuantity
from construction_pm.scheduling.time_forward_pass import TimeActivity, TimeRelationship, time_forward_pass
from construction_pm.scheduling.time_schedule import (
    calculate_time_floats,
    time_backward_pass,
    time_schedule,
)


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
    return CalendarResolverRegistry(
        time_resolvers={"site@1": TimeAwareWorkingTimeResolver(calendar)}
    )


def context():
    ref = CalendarReference("site", "1", "working-time")
    return SchedulingCalendarContext(project=ref, activity=ref, relationship_lag=ref)


def test_time_backward_pass_terminal_activity_respects_project_finish():
    ctx = context()
    activities = [TimeActivity("A", TimeQuantity.working_hours(4), ctx)]
    early = time_forward_pass(activities, [], datetime(2026, 9, 22, 8), registry())
    late = time_backward_pass(
        activities, [], early, datetime(2026, 9, 22, 17), registry()
    )
    assert late["A"].finish == datetime(2026, 9, 22, 17)
    assert late["A"].start == datetime(2026, 9, 22, 13)


def test_time_backward_pass_fs_inverse_matches_forward_boundary():
    ctx = context()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(4), ctx),
        TimeActivity("B", TimeQuantity.working_hours(2), ctx),
    ]
    relationships = [TimeRelationship("A", "B", RelationshipType.FS)]
    early = time_forward_pass(activities, relationships, datetime(2026, 9, 22, 8), registry())
    late = time_backward_pass(
        activities, relationships, early, datetime(2026, 9, 22, 17), registry()
    )
    assert late["B"].finish == datetime(2026, 9, 22, 17)
    assert late["B"].start == datetime(2026, 9, 22, 15)
    assert late["A"].finish == datetime(2026, 9, 22, 15)
    assert late["A"].start == datetime(2026, 9, 22, 10)


def test_time_backward_pass_supports_negative_lag():
    ctx = context()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(4), ctx),
        TimeActivity("B", TimeQuantity.working_hours(2), ctx),
    ]
    relationships = [
        TimeRelationship("A", "B", RelationshipType.FS, LagQuantity.working_hours(-1))
    ]
    early = time_forward_pass(activities, relationships, datetime(2026, 9, 22, 8), registry())
    late = time_backward_pass(
        activities, relationships, early, datetime(2026, 9, 22, 17), registry()
    )
    assert late["B"].start == datetime(2026, 9, 22, 15)
    assert late["A"].finish == datetime(2026, 9, 22, 16)


def test_time_schedule_produces_zero_float_for_terminal_path():
    ctx = context()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(4), ctx),
        TimeActivity("B", TimeQuantity.working_hours(2), ctx),
    ]
    relationships = [TimeRelationship("A", "B")]
    result = time_schedule(
        activities, relationships, datetime(2026, 9, 22, 8), datetime(2026, 9, 22, 15), registry()
    )
    assert result.floats["B"].total_float_hours == Decimal("0")
    assert result.floats["A"].total_float_hours == Decimal("0")
    assert result.floats["A"].critical


def test_time_schedule_retains_positive_float_for_noncritical_activity():
    ctx = context()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(2), ctx),
        TimeActivity("B", TimeQuantity.working_hours(2), ctx),
    ]
    result = time_schedule(
        activities, [], datetime(2026, 9, 22, 8), datetime(2026, 9, 22, 17), registry()
    )
    assert result.floats["A"].total_float_hours == Decimal("6")
    assert not result.floats["A"].critical


def test_time_schedule_uses_project_calendar_for_explicit_finish():
    project_ref = CalendarReference("project", "1", "working-time")
    activity_ref = CalendarReference("activity", "1", "working-time")
    project_calendar = WorkingTimeCalendar(
        daily_intervals={i: ((time(8), time(12)), (time(13), time(17))) for i in range(5)}
    )
    activity_calendar = WorkingTimeCalendar(
        daily_intervals={i: ((time(7), time(11)), (time(12), time(16))) for i in range(5)}
    )
    registry = CalendarResolverRegistry(time_resolvers={
        "project@1": TimeAwareWorkingTimeResolver(project_calendar),
        "activity@1": TimeAwareWorkingTimeResolver(activity_calendar),
    })
    ctx = SchedulingCalendarContext(project=project_ref, activity=activity_ref, relationship_lag=activity_ref)
    result = time_schedule(
        [TimeActivity("A", TimeQuantity.working_hours(2), ctx)],
        [],
        datetime(2026, 9, 22, 8),
        datetime(2026, 9, 22, 12),
        registry,
    )
    assert result.late_activities["A"].finish == datetime(2026, 9, 22, 12)
    assert result.late_activities["A"].start == datetime(2026, 9, 22, 10)


def test_time_backward_pass_does_not_use_last_activity_calendar_as_project_calendar():
    project_ref = CalendarReference("project", "1", "working-time")
    first_activity_ref = CalendarReference("first", "1", "working-time")
    last_activity_ref = CalendarReference("last", "1", "working-time")
    calendars = {
        "project@1": TimeAwareWorkingTimeResolver(WorkingTimeCalendar(
            daily_intervals={i: ((time(8), time(12)), (time(13), time(17))) for i in range(5)}
        )),
        "first@1": TimeAwareWorkingTimeResolver(WorkingTimeCalendar(
            daily_intervals={i: ((time(7), time(11)), (time(12), time(16))) for i in range(5)}
        )),
        "last@1": TimeAwareWorkingTimeResolver(WorkingTimeCalendar(
            daily_intervals={i: ((time(9), time(13)), (time(14), time(18))) for i in range(5)}
        )),
    }
    registry = CalendarResolverRegistry(time_resolvers=calendars)
    ctx_a = SchedulingCalendarContext(project=project_ref, activity=first_activity_ref, relationship_lag=first_activity_ref)
    ctx_b = SchedulingCalendarContext(project=project_ref, activity=last_activity_ref, relationship_lag=last_activity_ref)
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(2), ctx_a),
        TimeActivity("B", TimeQuantity.working_hours(2), ctx_b),
    ]
    early = time_forward_pass(activities, [TimeRelationship("A", "B")], datetime(2026, 9, 22, 8), registry)
    late = time_backward_pass(activities, [TimeRelationship("A", "B")], early, datetime(2026, 9, 22, 17), registry)
    assert late["B"].finish == datetime(2026, 9, 22, 17)
