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
from construction_pm.scheduling.time_constraints import TimeActivityConstraint, TimeConstraintType
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
    assert late["B"].finish == datetime(2026, 9, 22, 16)
    assert late["B"].start == datetime(2026, 9, 22, 14)
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
        datetime(2026, 9, 22, 12, 30),
        registry,
    )
    assert result.project_finish == datetime(2026, 9, 22, 12)
    assert result.late_activities["A"].finish == datetime(2026, 9, 22, 11)
    assert result.late_activities["A"].start == datetime(2026, 9, 22, 9)


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


def _cross_calendar_registry():
    project = TimeAwareWorkingTimeResolver(
        WorkingTimeCalendar(daily_intervals={i: ((time(8), time(12)), (time(13), time(17))) for i in range(5)})
    )
    predecessor = TimeAwareWorkingTimeResolver(
        WorkingTimeCalendar(daily_intervals={i: ((time(8), time(12)), (time(13), time(17))) for i in range(5)})
    )
    successor = TimeAwareWorkingTimeResolver(
        WorkingTimeCalendar(daily_intervals={i: ((time(7), time(11)), (time(12), time(16))) for i in range(5)})
    )
    lag = TimeAwareWorkingTimeResolver(
        WorkingTimeCalendar(daily_intervals={i: ((time(9), time(18)),) for i in range(5)})
    )
    return CalendarResolverRegistry(time_resolvers={
        "project@1": project,
        "predecessor@1": predecessor,
        "successor@1": successor,
        "lag@1": lag,
    })


def test_cross_calendar_fs_positive_lag_uses_successor_lag_calendar():
    refs = {
        "project": CalendarReference("project", "1", "working-time"),
        "predecessor": CalendarReference("predecessor", "1", "working-time"),
        "successor": CalendarReference("successor", "1", "working-time"),
        "lag": CalendarReference("lag", "1", "working-time"),
    }
    registry = _cross_calendar_registry()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(4), SchedulingCalendarContext(
            refs["project"], refs["predecessor"], refs["lag"]
        )),
        TimeActivity("B", TimeQuantity.working_hours(2), SchedulingCalendarContext(
            refs["project"], refs["successor"], refs["lag"]
        )),
    ]
    relationships = [TimeRelationship("A", "B", RelationshipType.FS, LagQuantity.working_hours(1))]
    early = time_forward_pass(activities, relationships, datetime(2026, 9, 22, 8), registry)
    assert early["A"].finish == datetime(2026, 9, 22, 12)
    assert early["B"].start == datetime(2026, 9, 22, 13)
    assert early["B"].finish == datetime(2026, 9, 22, 15)

    late = time_backward_pass(activities, relationships, early, datetime(2026, 9, 22, 17), registry)
    assert late["B"].start == datetime(2026, 9, 22, 14)
    assert late["B"].finish == datetime(2026, 9, 22, 16)
    assert late["A"].finish == datetime(2026, 9, 22, 12)
    assert late["A"].start == datetime(2026, 9, 22, 8)


def test_cross_calendar_ff_positive_lag_preserves_activity_and_lag_calendars():
    refs = {
        "project": CalendarReference("project", "1", "working-time"),
        "predecessor": CalendarReference("predecessor", "1", "working-time"),
        "successor": CalendarReference("successor", "1", "working-time"),
        "lag": CalendarReference("lag", "1", "working-time"),
    }
    registry = _cross_calendar_registry()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(4), SchedulingCalendarContext(
            refs["project"], refs["predecessor"], refs["lag"]
        )),
        TimeActivity("B", TimeQuantity.working_hours(2), SchedulingCalendarContext(
            refs["project"], refs["successor"], refs["lag"]
        )),
    ]
    relationships = [TimeRelationship("A", "B", RelationshipType.FF, LagQuantity.working_hours(1))]
    early = time_forward_pass(activities, relationships, datetime(2026, 9, 22, 8), registry)
    assert early["A"].finish == datetime(2026, 9, 22, 12)
    assert early["B"].start == datetime(2026, 9, 22, 10)
    assert early["B"].finish == datetime(2026, 9, 22, 13)

    late = time_backward_pass(activities, relationships, early, datetime(2026, 9, 22, 17), registry)
    assert late["B"].finish == datetime(2026, 9, 22, 16)
    assert late["A"].finish == datetime(2026, 9, 22, 15)


def test_cross_calendar_ss_negative_lag_and_float_remain_deterministic():
    refs = {
        "project": CalendarReference("project", "1", "working-time"),
        "predecessor": CalendarReference("predecessor", "1", "working-time"),
        "successor": CalendarReference("successor", "1", "working-time"),
        "lag": CalendarReference("lag", "1", "working-time"),
    }
    registry = _cross_calendar_registry()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(2), SchedulingCalendarContext(
            refs["project"], refs["predecessor"], refs["lag"]
        )),
        TimeActivity("B", TimeQuantity.working_hours(2), SchedulingCalendarContext(
            refs["project"], refs["successor"], refs["lag"]
        )),
    ]
    relationships = [TimeRelationship("A", "B", RelationshipType.SS, LagQuantity.working_hours(-1))]
    result = time_schedule(
        activities,
        relationships,
        datetime(2026, 9, 22, 8),
        datetime(2026, 9, 22, 17),
        registry,
    )
    assert result.early_activities["A"].start == datetime(2026, 9, 22, 8)
    assert result.early_activities["B"].start == datetime(2026, 9, 22, 7)
    assert result.early_activities["B"].finish == datetime(2026, 9, 22, 9)
    assert result.late_activities["B"].finish == datetime(2026, 9, 22, 16)
    assert result.floats["A"].total_float_hours == Decimal("6.0")
    assert not result.floats["A"].critical


def test_cross_calendar_sf_zero_lag_uses_successor_finish_event():
    refs = {
        "project": CalendarReference("project", "1", "working-time"),
        "predecessor": CalendarReference("predecessor", "1", "working-time"),
        "successor": CalendarReference("successor", "1", "working-time"),
        "lag": CalendarReference("lag", "1", "working-time"),
    }
    registry = _cross_calendar_registry()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(4), SchedulingCalendarContext(
            refs["project"], refs["predecessor"], refs["lag"]
        )),
        TimeActivity("B", TimeQuantity.working_hours(2), SchedulingCalendarContext(
            refs["project"], refs["successor"], refs["lag"]
        )),
    ]
    relationships = [TimeRelationship("A", "B", RelationshipType.SF)]
    early = time_forward_pass(activities, relationships, datetime(2026, 9, 22, 8), registry)
    assert early["A"].start == datetime(2026, 9, 22, 8)
    assert early["A"].finish == datetime(2026, 9, 22, 12)
    assert early["B"].start == datetime(2026, 9, 22, 7)
    assert early["B"].finish == datetime(2026, 9, 22, 9)

    late = time_backward_pass(activities, relationships, early, datetime(2026, 9, 22, 17), registry)
    assert late["B"].finish == datetime(2026, 9, 22, 16)
    assert late["B"].start == datetime(2026, 9, 22, 14)
    assert late["A"].start == datetime(2026, 9, 22, 13)
    assert late["A"].finish == datetime(2026, 9, 22, 17)


def test_cross_calendar_activity_constraint_uses_activity_calendar():
    refs = {
        "project": CalendarReference("project", "1", "working-time"),
        "predecessor": CalendarReference("predecessor", "1", "working-time"),
        "successor": CalendarReference("successor", "1", "working-time"),
        "lag": CalendarReference("lag", "1", "working-time"),
    }
    registry = _cross_calendar_registry()
    activity = TimeActivity(
        "A",
        TimeQuantity.working_hours(2),
        SchedulingCalendarContext(refs["project"], refs["successor"], refs["lag"]),
    )
    constraint = TimeActivityConstraint(
        "A",
        TimeConstraintType.START_NO_EARLIER_THAN,
        datetime(2026, 9, 22, 10, 30),
    )
    early = time_forward_pass(
        [activity], [], datetime(2026, 9, 22, 8), registry, [constraint]
    )
    assert early["A"].start == datetime(2026, 9, 22, 10, 30)
    assert early["A"].finish == datetime(2026, 9, 22, 13, 30)


def test_cross_calendar_negative_lag_sf_is_consistent_forward_backward():
    refs = {
        "project": CalendarReference("project", "1", "working-time"),
        "predecessor": CalendarReference("predecessor", "1", "working-time"),
        "successor": CalendarReference("successor", "1", "working-time"),
        "lag": CalendarReference("lag", "1", "working-time"),
    }
    registry = _cross_calendar_registry()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(4), SchedulingCalendarContext(
            refs["project"], refs["predecessor"], refs["lag"]
        )),
        TimeActivity("B", TimeQuantity.working_hours(2), SchedulingCalendarContext(
            refs["project"], refs["successor"], refs["lag"]
        )),
    ]
    relationships = [TimeRelationship("A", "B", RelationshipType.SF, LagQuantity.working_hours(-1))]
    early = time_forward_pass(activities, relationships, datetime(2026, 9, 22, 8), registry)
    assert early["B"].start == datetime(2026, 9, 21, 14)
    assert early["B"].finish == datetime(2026, 9, 21, 16)
    late = time_backward_pass(activities, relationships, early, datetime(2026, 9, 22, 17), registry)
    assert late["B"].finish == datetime(2026, 9, 22, 16)
    assert late["A"].start == datetime(2026, 9, 22, 13)
    assert late["A"].finish == datetime(2026, 9, 22, 18)


def test_cross_calendar_all_relationships_preserve_noncritical_float_when_unrelated():
    refs = {
        "project": CalendarReference("project", "1", "working-time"),
        "predecessor": CalendarReference("predecessor", "1", "working-time"),
        "successor": CalendarReference("successor", "1", "working-time"),
        "lag": CalendarReference("lag", "1", "working-time"),
    }
    registry = _cross_calendar_registry()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(2), SchedulingCalendarContext(
            refs["project"], refs["predecessor"], refs["lag"]
        )),
        TimeActivity("B", TimeQuantity.working_hours(2), SchedulingCalendarContext(
            refs["project"], refs["successor"], refs["lag"]
        )),
    ]
    result = time_schedule(
        activities,
        [TimeRelationship("A", "B", RelationshipType.SS, LagQuantity.working_hours(1))],
        datetime(2026, 9, 22, 8),
        datetime(2026, 9, 22, 17),
        registry,
    )
    assert result.floats["B"].total_float_hours == Decimal("3.0")
    assert result.floats["B"].critical is False
