from datetime import date
from decimal import Decimal

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.authoritative_schedule_batch import (
    UnsupportedMultiProjectSchedulingError,
    execute_authoritative_schedule_batch,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
)
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.resource_leveling import (
    BackwardLevelingActivity,
    LevelingActivity,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingOptions,
)
from construction_pm.scheduling.relationships import Relationship
from construction_pm.scheduling.schedule_options import ScheduleOptions


def _calendar_registry():
    project_resolver = WorkingTimeResolver(WorkingCalendar())
    weekend_resolver = WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset(range(7)))
    )
    return project_resolver, CalendarResolverRegistry(
        {
            "CAL@1": project_resolver,
            "WEEKEND@1": weekend_resolver,
        }
    )


def _snapshot(project_id, finish, *, assignment=None, options=None):
    return AuthoritativeScheduleInput(
        snapshot_id=f"s-{project_id}",
        tenant_id="tenant",
        project_id=project_id,
        project_revision=1,
        project_leveling_priority=10,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL", "1"),
        activities=(Activity(f"{project_id}-A", 1),),
        relationships=(),
        activity_calendar_assignments=(
            (assignment,) if assignment is not None else ()
        ),
        project_finish=finish,
        project_start=date(2026, 10, 1),
        schedule_options=options or ScheduleOptions(),
    )


def test_mixed_activity_calendars_execute_inside_authoritative_batch_cpm():
    project_resolver, registry = _calendar_registry()
    p1 = _snapshot("P1", date(2026, 10, 10))
    p2 = _snapshot(
        "P2",
        date(2026, 10, 10),
        assignment=ActivityCalendarAssignment(
            "P2-A", CalendarReference("WEEKEND", "1")
        ),
    )

    result = execute_authoritative_schedule_batch(
        [p1, p2],
        resolvers={"P1": project_resolver, "P2": project_resolver},
        calendar_registry=registry,
        external_relationships=(Relationship("P1-A", "P2-A"),),
        activity_project_ids={"P1-A": "P1", "P2-A": "P2"},
    )

    p1_early = result.project("P1").result.early_activities
    p2_early = result.project("P2").result.early_activities
    assert p1_early is not None and p2_early is not None
    assert p1_early["P1-A"].finish == date(2026, 10, 1)
    assert p2_early["P2-A"].start == date(2026, 10, 2)
    assert p2_early["P2-A"].finish == date(2026, 10, 2)


def test_mixed_activity_calendar_batch_leveling_is_explicitly_guarded():
    project_resolver, registry = _calendar_registry()
    options = ScheduleOptions(level_all_resources=True)
    p1 = _snapshot("P1", date(2026, 10, 10), options=options)
    p2 = _snapshot(
        "P2",
        date(2026, 10, 10),
        assignment=ActivityCalendarAssignment(
            "P2-A", CalendarReference("WEEKEND", "1")
        ),
        options=options,
    )
    demand_1 = ResourceDemand("R1", date(2026, 10, 1), Decimal("1"), "P1-A")
    demand_2 = ResourceDemand("R1", date(2026, 10, 1), Decimal("1"), "P2-A")
    leveling = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity(
                "P1-A", date(2026, 10, 1), date(2026, 10, 1), 0, (demand_1,)
            ),
            LevelingActivity(
                "P2-A", date(2026, 10, 1), date(2026, 10, 1), 0, (demand_2,)
            ),
        ),
        backward_activities=(
            BackwardLevelingActivity(
                "P1-A", date(2026, 10, 1), date(2026, 10, 1),
                date(2026, 10, 10), date(2026, 10, 10), (demand_1,)
            ),
            BackwardLevelingActivity(
                "P2-A", date(2026, 10, 1), date(2026, 10, 1),
                date(2026, 10, 10), date(2026, 10, 10), (demand_2,)
            ),
        ),
        capacities=(
            ResourceCapacity("R1", date(2026, 10, 1), Decimal("1")),
        ),
        options=ResourceLevelingOptions(level_all_resources=True),
    )

    with pytest.raises(
        UnsupportedMultiProjectSchedulingError,
        match="MULTI_PROJECT_RESOURCE_LEVELING_MIXED_ACTIVITY_CALENDARS_NOT_SUPPORTED",
    ):
        execute_authoritative_schedule_batch(
            [p1, p2],
            resolvers={"P1": project_resolver, "P2": project_resolver},
            calendar_registry=registry,
            leveling_input=leveling,
        )
