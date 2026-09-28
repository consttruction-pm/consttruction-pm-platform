from datetime import date, datetime, time
from decimal import Decimal

import pytest

from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
    SchedulingCalendarContext,
)
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_calendar import (
    TimeAwareWorkingTimeResolver,
    WorkingTimeCalendar,
)
from construction_pm.scheduling.time_duration import LagQuantity, TimeQuantity
from construction_pm.scheduling.schedule_options import StartToStartLagCalculationType
from construction_pm.scheduling.time_forward_pass import (
    TimeActivity,
    TimeRelationship,
    time_forward_pass,
)


def registry():
    calendar = WorkingTimeCalendar(
        holidays=frozenset({date(2026, 9, 23)}),
        daily_intervals={
            0: ((time(8), time(12)), (time(13), time(17))),
            1: ((time(8), time(12)), (time(13), time(17))),
            2: ((time(8), time(12)), (time(13), time(17))),
            3: ((time(8), time(12)), (time(13), time(17))),
            4: ((time(8), time(12)), (time(13), time(17))),
        },
    )
    return CalendarResolverRegistry(
        time_resolvers={"site@1": TimeAwareWorkingTimeResolver(calendar)}
    )


def context():
    ref = CalendarReference("site", "1", "working-time")
    return SchedulingCalendarContext(
        project=ref,
        activity=ref,
        relationship_lag=ref,
    )


def test_time_forward_pass_schedules_working_hour_duration_across_break():
    ctx = context()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(5), ctx),
    ]
    result = time_forward_pass(
        activities, [], datetime(2026, 9, 22, 10), registry()
    )
    assert result["A"].start == datetime(2026, 9, 22, 10)
    assert result["A"].finish == datetime(2026, 9, 22, 16)


def test_time_forward_pass_fs_zero_uses_exact_finish_boundary():
    ctx = context()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(4), ctx),
        TimeActivity("B", TimeQuantity.working_hours(2), ctx),
    ]
    result = time_forward_pass(
        activities,
        [TimeRelationship("A", "B", RelationshipType.FS)],
        datetime(2026, 9, 22, 8),
        registry(),
    )
    assert result["A"].finish == datetime(2026, 9, 22, 12)
    assert result["B"].start == datetime(2026, 9, 22, 13)


def test_time_forward_pass_ss_positive_lag_uses_working_hours():
    ctx = context()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(2), ctx),
        TimeActivity("B", TimeQuantity.working_hours(1), ctx),
    ]
    result = time_forward_pass(
        activities,
        [TimeRelationship("A", "B", RelationshipType.SS, LagQuantity.working_hours(2))],
        datetime(2026, 9, 22, 8),
        registry(),
    )
    assert result["B"].start == datetime(2026, 9, 22, 10)


def test_time_forward_pass_ff_positive_lag_preserves_finish_relation():
    ctx = context()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(2), ctx),
        TimeActivity("B", TimeQuantity.working_hours(2), ctx),
    ]
    result = time_forward_pass(
        activities,
        [TimeRelationship("A", "B", RelationshipType.FF, LagQuantity.working_hours(1))],
        datetime(2026, 9, 22, 8),
        registry(),
    )
    assert result["B"].finish == datetime(2026, 9, 22, 11)
    assert result["B"].start == datetime(2026, 9, 22, 9)


def test_time_forward_pass_skips_holiday_for_positive_lag():
    ctx = context()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(8), ctx),
        TimeActivity("B", TimeQuantity.working_hours(1), ctx),
    ]
    result = time_forward_pass(
        activities,
        [TimeRelationship("A", "B", RelationshipType.FS, LagQuantity.working_hours(2))],
        datetime(2026, 9, 22, 8),
        registry(),
    )
    assert result["B"].start == datetime(2026, 9, 24, 10)


def test_time_forward_pass_rejects_implicit_working_day_conversion():
    ctx = context()
    activities = [
        TimeActivity("A", TimeQuantity.working_days(1), ctx),
    ]
    with pytest.raises(NotImplementedError):
        time_forward_pass(activities, [], datetime(2026, 9, 22, 8), registry())


def test_time_forward_pass_supports_negative_hour_lag():
    ctx = context()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(4), ctx),
        TimeActivity("B", TimeQuantity.working_hours(2), ctx),
    ]
    result = time_forward_pass(
        activities,
        [TimeRelationship("A", "B", lag=LagQuantity.working_hours(-1))],
        datetime(2026, 9, 22, 8),
        registry(),
    )
    assert result["A"].finish == datetime(2026, 9, 22, 12)
    assert result["B"].start == datetime(2026, 9, 22, 11)

def test_time_forward_pass_sf_zero_uses_predecessor_start():
    ctx = context()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(4), ctx),
        TimeActivity("B", TimeQuantity.working_hours(2), ctx),
    ]
    result = time_forward_pass(
        activities,
        [TimeRelationship("A", "B", RelationshipType.SF)],
        datetime(2026, 9, 22, 8),
        registry(),
    )
    assert result["A"].start == datetime(2026, 9, 22, 8)
    assert result["B"].finish == datetime(2026, 9, 21, 17)


def test_time_forward_pass_uses_authoritative_project_calendar_for_root_start():
    project_ref = CalendarReference("project", "1", "working-time")
    activity_ref = CalendarReference("activity", "1", "working-time")
    project_calendar = WorkingTimeCalendar(
        holidays=frozenset({date(2026, 9, 22)}),
        daily_intervals={i: ((time(8), time(12)), (time(13), time(17))) for i in range(5)},
    )
    activity_calendar = WorkingTimeCalendar(
        daily_intervals={i: ((time(7), time(11)), (time(12), time(16))) for i in range(5)},
    )
    registry = CalendarResolverRegistry(time_resolvers={
        "project@1": TimeAwareWorkingTimeResolver(project_calendar),
        "activity@1": TimeAwareWorkingTimeResolver(activity_calendar),
    })
    context = SchedulingCalendarContext(
        project=project_ref,
        activity=activity_ref,
        relationship_lag=activity_ref,
    )

    result = time_forward_pass(
        [TimeActivity("A", TimeQuantity.working_hours(1), context)],
        [],
        datetime(2026, 9, 22, 8),
        registry,
    )

    assert result["A"].start == datetime(2026, 9, 23, 8)
    assert result["A"].finish == datetime(2026, 9, 23, 9)


def test_time_forward_pass_rejects_mixed_project_calendar_references_before_scheduling():
    project_a = CalendarReference("project-a", "1", "working-time")
    project_b = CalendarReference("project-b", "1", "working-time")
    activity_ref = CalendarReference("activity", "1", "working-time")
    resolver = TimeAwareWorkingTimeResolver(WorkingTimeCalendar())
    registry = CalendarResolverRegistry(time_resolvers={
        "project-a@1": resolver,
        "project-b@1": resolver,
        "activity@1": resolver,
    })
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(1), SchedulingCalendarContext(
            project_a, activity_ref, activity_ref
        )),
        TimeActivity("B", TimeQuantity.working_hours(1), SchedulingCalendarContext(
            project_b, activity_ref, activity_ref
        )),
    ]

    with pytest.raises(ValueError, match="must share one project calendar"):
        time_forward_pass(
            activities, [], datetime(2026, 9, 22, 8), registry
        )


def test_time_forward_pass_requires_registered_project_calendar():
    project_ref = CalendarReference("project", "1", "working-time")
    activity_ref = CalendarReference("activity", "1", "working-time")
    registry = CalendarResolverRegistry(time_resolvers={
        "activity@1": TimeAwareWorkingTimeResolver(WorkingTimeCalendar()),
    })
    activity = TimeActivity(
        "A",
        TimeQuantity.working_hours(1),
        SchedulingCalendarContext(project_ref, activity_ref, activity_ref),
    )

    with pytest.raises(KeyError, match="calendar not registered: project@1"):
        time_forward_pass(
            [activity], [], datetime(2026, 9, 22, 8), registry
        )


@pytest.mark.parametrize(
    ("lag_mode", "expected_start"),
    [
        (StartToStartLagCalculationType.EARLY_START, datetime(2026, 9, 22, 13)),
        (StartToStartLagCalculationType.ACTUAL_START, datetime(2026, 9, 24, 15)),
    ],
)
def test_time_forward_pass_start_to_start_out_of_sequence_uses_selected_anchor(
    lag_mode, expected_start
):
    ctx = context()
    activities = [
        TimeActivity(
            "A",
            TimeQuantity.working_hours(2),
            ctx,
            actual_start=datetime(2026, 9, 22, 10),
        ),
        TimeActivity("B", TimeQuantity.working_hours(1), ctx),
    ]
    result = time_forward_pass(
        activities,
        [TimeRelationship("A", "B", RelationshipType.SS, LagQuantity.working_hours(12))],
        datetime(2026, 9, 22, 8),
        registry(),
        start_to_start_lag_calculation_type=lag_mode,
        data_date=datetime(2026, 9, 24, 10),
    )
    assert result["A"].start == datetime(2026, 9, 22, 8)
    assert result["B"].start == expected_start


def test_time_forward_pass_start_to_start_out_of_sequence_requires_data_date():
    ctx = context()
    activities = [
        TimeActivity(
            "A",
            TimeQuantity.working_hours(2),
            ctx,
            actual_start=datetime(2026, 9, 22, 10),
        ),
        TimeActivity("B", TimeQuantity.working_hours(1), ctx),
    ]
    with pytest.raises(ValueError, match="data_date is required"):
        time_forward_pass(
            activities,
            [TimeRelationship("A", "B", RelationshipType.SS, LagQuantity.working_hours(4))],
            datetime(2026, 9, 22, 8),
            registry(),
        )
