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
