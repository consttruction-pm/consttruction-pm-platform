from datetime import date, datetime

import pytest

from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
    SchedulingCalendarContext,
)
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import DurationUnit, LagQuantity, TimeQuantity
from construction_pm.scheduling.time_forward_pass import TimeActivity, TimeRelationship, time_forward_pass
from construction_pm.scheduling.time_schedule import time_schedule


def day_registry():
    project = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({date(2026, 9, 23)}))
    )
    activity = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({date(2026, 9, 23)}))
    )
    ref_project = CalendarReference("project-day", "1", "working-day")
    ref_activity = CalendarReference("activity-day", "1", "working-day")
    registry = CalendarResolverRegistry(
        day_resolvers={
            "project-day@1": project,
            "activity-day@1": activity,
        }
    )
    ctx = SchedulingCalendarContext(ref_project, ref_activity, ref_activity)
    return registry, ctx


def test_working_day_forward_pass_schedules_duration_and_skips_holiday():
    registry, ctx = day_registry()
    result = time_forward_pass(
        [TimeActivity("A", TimeQuantity.working_days(2), ctx)],
        [],
        datetime(2026, 9, 22, 8),
        registry,
    )
    assert result["A"].start == datetime(2026, 9, 22)
    assert result["A"].finish == datetime(2026, 9, 24)


def test_working_day_schedule_runs_backward_and_reports_unit_correct_float():
    registry, ctx = day_registry()
    result = time_schedule(
        [TimeActivity("A", TimeQuantity.working_days(2), ctx)],
        [],
        datetime(2026, 9, 22, 8),
        datetime(2026, 9, 25, 8),
        registry,
    )
    assert result.early_activities["A"].start == datetime(2026, 9, 22)
    assert result.early_activities["A"].finish == datetime(2026, 9, 24)
    assert result.late_activities["A"].start == datetime(2026, 9, 24)
    assert result.late_activities["A"].finish == datetime(2026, 9, 24)
    assert result.floats["A"].float_unit is DurationUnit.WORKING_DAY
    assert result.floats["A"].total_float_value == 2
    assert result.floats["A"].total_float_hours is None


def test_working_day_calendar_rejects_working_hour_duration_instead_of_converting():
    registry, ctx = day_registry()
    with pytest.raises(ValueError, match="working-day calendar requires working-day duration"):
        time_forward_pass(
            [TimeActivity("A", TimeQuantity.working_hours(8), ctx)],
            [],
            datetime(2026, 9, 22, 8),
            registry,
        )


def test_working_day_calendar_rejects_working_hour_relationship_lag_instead_of_converting():
    registry, ctx = day_registry()
    activities = [
        TimeActivity("A", TimeQuantity.working_days(1), ctx),
        TimeActivity("B", TimeQuantity.working_days(1), ctx),
    ]
    with pytest.raises(ValueError, match="working-day lag calendar requires working-day lag"):
        time_forward_pass(
            activities,
            [TimeRelationship("A", "B", RelationshipType.FS, LagQuantity.working_hours(8))],
            datetime(2026, 9, 22, 8),
            registry,
        )
