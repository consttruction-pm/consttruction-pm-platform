from datetime import date, datetime, timezone

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.activity_calendar_context import (
    ActivityCalendarContext,
    ActivityCalendarContextError,
)
from construction_pm.scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.time_duration import TimeQuantity
from construction_pm.scheduling.time_forward_pass import TimeActivity
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
)


CAL_PROJECT = CalendarReference("PROJECT", "1")
CAL_WEEKEND = CalendarReference("WEEKEND", "1")


def registry() -> CalendarResolverRegistry:
    return CalendarResolverRegistry(
        {
            "PROJECT@1": WorkingTimeResolver(WorkingCalendar()),
            "WEEKEND@1": WorkingTimeResolver(
                WorkingCalendar(working_weekdays=frozenset(range(7)))
            ),
        }
    )


def snapshot(assignments=()):
    return AuthoritativeScheduleInput(
        snapshot_id="s-P1",
        tenant_id="tenant",
        project_id="P1",
        project_revision=1,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CAL_PROJECT,
        activities=(Activity("A", 2),),
        relationships=(),
        activity_calendar_assignments=tuple(assignments),
        project_start=date(2026, 9, 25),
        project_finish=date(2026, 9, 29),
    )


def test_activity_calendar_context_uses_assignment_or_project_default():
    context = ActivityCalendarContext.from_snapshots(
        [snapshot([ActivityCalendarAssignment("A", CAL_WEEKEND)])],
        registry(),
    )
    assert context.for_activity("A").calendar.working_weekdays == frozenset(range(7))

    default_context = ActivityCalendarContext.from_snapshots([snapshot()], registry())
    assert default_context.for_activity("A").calendar.working_weekdays != frozenset(range(7))


def test_activity_calendar_context_rejects_unresolved_calendar():
    missing = CalendarReference("MISSING", "1")
    with pytest.raises(ActivityCalendarContextError, match="calendar cannot be resolved"):
        ActivityCalendarContext.from_snapshots(
            [snapshot([ActivityCalendarAssignment("A", missing)])],
            registry(),
        )


def test_activity_calendar_context_rejects_mixed_time_aware_batch():
    timeaware_calendar = CalendarReference("PROJECT-TIME", "1", "working-time")
    timeaware = AuthoritativeScheduleInput(
        snapshot_id="s-P2",
        tenant_id="tenant",
        project_id="P2",
        project_revision=1,
        mode=AuthoritativeScheduleMode.TIME_AWARE,
        project_calendar=timeaware_calendar,
        activities=(TimeActivity("T", TimeQuantity.working_hours(8)),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=datetime(2026, 9, 25, tzinfo=timezone.utc),
        project_finish=datetime(2026, 9, 29, tzinfo=timezone.utc),
    )
    with pytest.raises(ActivityCalendarContextError, match="DATE_BASED snapshots only"):
        ActivityCalendarContext.from_snapshots([snapshot(), timeaware], registry())


def test_activity_calendar_context_rejects_duplicate_activity_ids():
    duplicate = AuthoritativeScheduleInput(
        snapshot_id="s-P2",
        tenant_id="tenant",
        project_id="P2",
        project_revision=1,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CAL_PROJECT,
        activities=(Activity("A", 1),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 25),
        project_finish=date(2026, 9, 29),
    )
    with pytest.raises(ActivityCalendarContextError, match="duplicate activity id"):
        ActivityCalendarContext.from_snapshots([snapshot(), duplicate], registry())


def test_activity_calendar_context_has_immutable_resolver_mapping():
    context = ActivityCalendarContext.from_snapshots([snapshot()], registry())
    with pytest.raises(TypeError):
        context.resolvers["A"] = registry().resolve(CAL_PROJECT)
