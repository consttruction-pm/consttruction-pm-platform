from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.out_of_sequence import (
    ProgressRelationAction,
    predecessor_event_for_oos,
    resolve_out_of_sequence_action,
)
from construction_pm.scheduling.forward_pass import ScheduledActivity
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.schedule_options import OutOfSequenceScheduleType


@pytest.fixture
def resolver():
    return WorkingTimeResolver(WorkingCalendar())


def test_retained_logic_keeps_relationship_anchor(resolver):
    activity = Activity("A", 5, actual_start=date(2026, 9, 24))
    scheduled = ScheduledActivity("A", date(2026, 9, 21), date(2026, 9, 25), 5)
    anchor, action = predecessor_event_for_oos(
        Relationship("A", "B", RelationshipType.FS),
        activity,
        scheduled,
        resolver=resolver,
        data_date=date(2026, 9, 28),
        mode=OutOfSequenceScheduleType.RETAINED_LOGIC,
    )
    assert action is ProgressRelationAction.APPLY_LOGIC
    assert anchor == scheduled.finish


def test_progress_override_does_not_reapply_predecessor_relationship(resolver):
    activity = Activity("A", 5, actual_start=date(2026, 9, 24))
    scheduled = ScheduledActivity("A", date(2026, 9, 21), date(2026, 9, 25), 5)
    anchor, action = predecessor_event_for_oos(
        Relationship("A", "B", RelationshipType.FS),
        activity,
        scheduled,
        resolver=resolver,
        data_date=date(2026, 9, 28),
        mode=OutOfSequenceScheduleType.PROGRESS_OVERRIDE,
    )
    assert action is ProgressRelationAction.IGNORE_LOGIC
    assert anchor is None


def test_actual_dates_uses_actual_start_for_ss_and_sf(resolver):
    activity = Activity("A", 5, actual_start=date(2026, 9, 24))
    scheduled = ScheduledActivity("A", date(2026, 9, 21), date(2026, 9, 25), 5)
    for relationship_type in (RelationshipType.SS, RelationshipType.SF):
        anchor, action = predecessor_event_for_oos(
            Relationship("A", "B", relationship_type),
            activity,
            scheduled,
            resolver=resolver,
            data_date=date(2026, 9, 28),
            mode=OutOfSequenceScheduleType.ACTUAL_DATES,
        )
        assert action is ProgressRelationAction.USE_ACTUAL_DATES
        assert anchor == date(2026, 9, 24)


def test_actual_dates_uses_actual_finish_for_fs_and_ff(resolver):
    activity = Activity(
        "A",
        5,
        actual_start=date(2026, 9, 21),
        actual_finish=date(2026, 9, 28),
        remaining_duration=0,
        percent_complete=100,
    )
    scheduled = ScheduledActivity("A", date(2026, 9, 21), date(2026, 9, 25), 5)
    for relationship_type in (RelationshipType.FS, RelationshipType.FF):
        anchor, action = predecessor_event_for_oos(
            Relationship("A", "B", relationship_type),
            activity,
            scheduled,
            resolver=resolver,
            data_date=date(2026, 9, 28),
            mode=OutOfSequenceScheduleType.ACTUAL_DATES,
        )
        assert action is ProgressRelationAction.USE_ACTUAL_DATES
        assert anchor == date(2026, 9, 28)


def test_oos_requires_data_date_for_started_activity():
    activity = Activity("A", 1, actual_start=date(2026, 9, 21))
    with pytest.raises(ValueError, match="data_date"):
        resolve_out_of_sequence_action(
            activity,
            data_date=None,
            mode=OutOfSequenceScheduleType.RETAINED_LOGIC,
        )


def test_oos_rejects_data_date_before_actual_start():
    activity = Activity("A", 1, actual_start=date(2026, 9, 21))
    with pytest.raises(ValueError, match="must not precede"):
        resolve_out_of_sequence_action(
            activity,
            data_date=date(2026, 9, 18),
            mode=OutOfSequenceScheduleType.ACTUAL_DATES,
        )


def test_unstarted_activity_does_not_trigger_oos():
    activity = Activity("A", 1)
    action = resolve_out_of_sequence_action(
        activity,
        data_date=date(2026, 9, 28),
        mode=OutOfSequenceScheduleType.PROGRESS_OVERRIDE,
    )
    assert action is ProgressRelationAction.APPLY_LOGIC
