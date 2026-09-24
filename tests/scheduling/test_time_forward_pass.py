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
