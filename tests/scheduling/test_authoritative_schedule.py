from datetime import date, datetime, timezone

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calendar_context import CalendarReference
from construction_pm.scheduling.relationships import Relationship
from construction_pm.scheduling.schedule import ScheduleOptions


def make_input() -> AuthoritativeScheduleInput:
    calendar = CalendarReference("CAL-1", "7")
    return AuthoritativeScheduleInput(
        snapshot_id="SNAP-1",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=7,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=calendar,
        activities=(Activity("A", 2), Activity("B", 1)),
        relationships=(Relationship("A", "B"),),
        activity_calendar_assignments=(
            ActivityCalendarAssignment("A", calendar),
            ActivityCalendarAssignment("B", calendar),
        ),
        schedule_options=ScheduleOptions(),
        project_start=date(2026, 9, 21),
    )


def test_snapshot_contract_is_deterministic():
    first = make_input()
    second = make_input()
    assert first.canonical_json() == second.canonical_json()
    assert first.snapshot_hash == second.snapshot_hash


def test_snapshot_rejects_cross_scope_activity_references():
    calendar = CalendarReference("CAL-1", "1")
    with pytest.raises(ValueError, match="unknown activity"):
        AuthoritativeScheduleInput(
            snapshot_id="S",
            tenant_id="T",
            project_id="P",
            project_revision=0,
            mode=AuthoritativeScheduleMode.DATE_BASED,
            project_calendar=calendar,
            activities=(Activity("A", 1),),
            relationships=(Relationship("A", "B"),),
            activity_calendar_assignments=(),
            project_start=date(2026, 9, 21),
        )


def test_date_based_contract_rejects_working_time_calendars():
    calendar = CalendarReference("CAL-1", "1", "working-time")
    with pytest.raises(ValueError, match="working-day project calendar"):
        AuthoritativeScheduleInput(
            snapshot_id="S", tenant_id="T", project_id="P", project_revision=0,
            mode=AuthoritativeScheduleMode.DATE_BASED, project_calendar=calendar,
            activities=(Activity("A", 1),), relationships=(),
            activity_calendar_assignments=(), project_start=date(2026, 9, 21),
        )


def test_date_based_contract_rejects_working_time_activity_assignment():
    project = CalendarReference("CAL-1", "1")
    time_calendar = CalendarReference("CAL-2", "1", "working-time")
    with pytest.raises(ValueError, match="working-day activity calendars"):
        AuthoritativeScheduleInput(
            snapshot_id="S", tenant_id="T", project_id="P", project_revision=0,
            mode=AuthoritativeScheduleMode.DATE_BASED, project_calendar=project,
            activities=(Activity("A", 1),), relationships=(),
            activity_calendar_assignments=(ActivityCalendarAssignment("A", time_calendar),),
            project_start=date(2026, 9, 21),
        )


def test_time_aware_contract_rejects_working_day_project_calendar():
    from construction_pm.scheduling.time_duration import TimeQuantity
    from construction_pm.scheduling.time_forward_pass import TimeActivity
    calendar = CalendarReference("CAL-1", "1")
    activity = TimeActivity("A", TimeQuantity.working_hours(2))
    with pytest.raises(ValueError, match="working-time project calendar"):
        AuthoritativeScheduleInput(
            snapshot_id="S", tenant_id="T", project_id="P", project_revision=0,
            mode=AuthoritativeScheduleMode.TIME_AWARE, project_calendar=calendar,
            activities=(activity,), relationships=(),
            activity_calendar_assignments=(),
            project_start=datetime(2026, 9, 21, 8, tzinfo=timezone.utc),
        )


def test_date_based_contract_requires_date_start():
    calendar = CalendarReference("CAL-1", "1")
    with pytest.raises(ValueError, match="project_start date"):
        AuthoritativeScheduleInput(
            snapshot_id="S",
            tenant_id="T",
            project_id="P",
            project_revision=0,
            mode=AuthoritativeScheduleMode.DATE_BASED,
            project_calendar=calendar,
            activities=(Activity("A", 1),),
            relationships=(),
            activity_calendar_assignments=(),
            project_start=datetime(2026, 9, 21, tzinfo=timezone.utc),
        )


def test_time_aware_contract_requires_timezone():
    from construction_pm.scheduling.time_duration import TimeQuantity
    from construction_pm.scheduling.time_forward_pass import TimeActivity

    calendar = CalendarReference("CAL-1", "1", "working-time")
    activity = TimeActivity("A", TimeQuantity.working_hours(2))
    with pytest.raises(ValueError, match="timezone"):
        AuthoritativeScheduleInput(
            snapshot_id="S",
            tenant_id="T",
            project_id="P",
            project_revision=0,
            mode=AuthoritativeScheduleMode.TIME_AWARE,
            project_calendar=calendar,
            activities=(activity,),
            relationships=(),
            activity_calendar_assignments=(),
            project_start=datetime(2026, 9, 21, 8, 0),
        )


def test_project_leveling_priority_is_validated_and_hashed():
    first = make_input()
    second = AuthoritativeScheduleInput(
        snapshot_id=first.snapshot_id,
        tenant_id=first.tenant_id,
        project_id=first.project_id,
        project_revision=first.project_revision,
        mode=first.mode,
        project_calendar=first.project_calendar,
        activities=first.activities,
        relationships=first.relationships,
        activity_calendar_assignments=first.activity_calendar_assignments,
        schedule_options=first.schedule_options,
        project_start=first.project_start,
        project_leveling_priority=5,
    )
    assert first.project_leveling_priority == 10
    assert second.project_leveling_priority == 5
    assert first.snapshot_hash != second.snapshot_hash


@pytest.mark.parametrize("priority", [0, 101, True])
def test_project_leveling_priority_rejects_invalid_values(priority):
    with pytest.raises(ValueError, match="project_leveling_priority"):
        AuthoritativeScheduleInput(
            snapshot_id="S",
            tenant_id="T",
            project_id="P",
            project_revision=0,
            mode=AuthoritativeScheduleMode.DATE_BASED,
            project_calendar=CalendarReference("CAL-1", "1"),
            activities=(Activity("A", 1),),
            relationships=(),
            activity_calendar_assignments=(),
            project_start=date(2026, 9, 21),
            project_leveling_priority=priority,
        )
