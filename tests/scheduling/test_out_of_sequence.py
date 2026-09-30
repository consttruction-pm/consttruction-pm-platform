from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.out_of_sequence import (
    OutOfSequenceState,
    ProgressRelationAction,
    classify_out_of_sequence,
    resolve_out_of_sequence_action,
)
from construction_pm.scheduling.schedule_options import OutOfSequenceScheduleType


def test_unstarted_activity_is_not_oos():
    activity = Activity("B", 5)
    assert classify_out_of_sequence(
        activity,
        relationship_required_start=date(2026, 9, 28),
        data_date=date(2026, 9, 30),
    ) is OutOfSequenceState.NOT_STARTED


def test_started_after_relationship_requirement_is_in_sequence():
    activity = Activity("B", 5, actual_start=date(2026, 9, 29))
    assert classify_out_of_sequence(
        activity,
        relationship_required_start=date(2026, 9, 28),
        data_date=date(2026, 9, 30),
    ) is OutOfSequenceState.IN_SEQUENCE


def test_started_before_relationship_requirement_is_out_of_sequence():
    activity = Activity("B", 5, actual_start=date(2026, 9, 24))
    assert classify_out_of_sequence(
        activity,
        relationship_required_start=date(2026, 9, 28),
        data_date=date(2026, 9, 30),
    ) is OutOfSequenceState.OUT_OF_SEQUENCE


@pytest.mark.parametrize(
    ("mode", "action"),
    [
        (OutOfSequenceScheduleType.RETAINED_LOGIC, ProgressRelationAction.APPLY_LOGIC),
        (OutOfSequenceScheduleType.PROGRESS_OVERRIDE, ProgressRelationAction.IGNORE_LOGIC),
        (OutOfSequenceScheduleType.ACTUAL_DATES, ProgressRelationAction.USE_ACTUAL_DATES),
    ],
)
def test_oos_mode_maps_only_after_oos_is_confirmed(mode, action):
    activity = Activity("B", 5, actual_start=date(2026, 9, 24))
    assert resolve_out_of_sequence_action(
        activity,
        relationship_required_start=date(2026, 9, 28),
        data_date=date(2026, 9, 30),
        mode=mode,
    ) is action


def test_in_sequence_progress_keeps_relationship_logic_for_all_modes():
    activity = Activity("B", 5, actual_start=date(2026, 9, 29))
    for mode in OutOfSequenceScheduleType:
        assert resolve_out_of_sequence_action(
            activity,
            relationship_required_start=date(2026, 9, 28),
            data_date=date(2026, 9, 30),
            mode=mode,
        ) is ProgressRelationAction.APPLY_LOGIC


def test_oos_requires_data_date_not_before_actual_start():
    activity = Activity("B", 5, actual_start=date(2026, 9, 29))
    with pytest.raises(ValueError, match="must not precede"):
        classify_out_of_sequence(
            activity,
            relationship_required_start=date(2026, 9, 28),
            data_date=date(2026, 9, 28),
        )


def test_relationship_required_start_supports_all_relationship_types():
    from construction_pm.scheduling.forward_pass import ScheduledActivity
    from construction_pm.scheduling.relationships import Relationship, RelationshipType
    from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
    from construction_pm.scheduling.out_of_sequence import relationship_required_start

    resolver = WorkingTimeResolver(WorkingCalendar())
    predecessor = ScheduledActivity("P", date(2026, 9, 28), date(2026, 9, 30), 2)

    for relationship_type in RelationshipType:
        relationship = Relationship("P", "S", relationship_type, 0)
        required = relationship_required_start(
            relationship, predecessor, 2, resolver=resolver
        )
        assert isinstance(required, date)
