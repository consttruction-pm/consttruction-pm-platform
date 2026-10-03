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

from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.schedule import ScheduleOptions, schedule


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


@pytest.mark.parametrize("relationship_type", __import__(
    "construction_pm.scheduling.relationships", fromlist=["RelationshipType"]
).RelationshipType)
@pytest.mark.parametrize("mode, expected_action", [
    (OutOfSequenceScheduleType.RETAINED_LOGIC, ProgressRelationAction.APPLY_LOGIC),
    (OutOfSequenceScheduleType.PROGRESS_OVERRIDE, ProgressRelationAction.IGNORE_LOGIC),
    (OutOfSequenceScheduleType.ACTUAL_DATES, ProgressRelationAction.USE_ACTUAL_DATES),
])
def test_oos_reference_matrix_four_relationships_three_modes(relationship_type, mode, expected_action):
    from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
    from construction_pm.scheduling.forward_pass import ScheduledActivity
    from construction_pm.scheduling.out_of_sequence import relationship_required_start
    from construction_pm.scheduling.relationships import Relationship

    resolver = WorkingTimeResolver(WorkingCalendar())
    predecessor = ScheduledActivity(
        "P", date(2026, 9, 28), date(2026, 9, 30), 2
    )
    relationship = Relationship("P", "S", relationship_type, 0)
    required = relationship_required_start(
        relationship, predecessor, 2, resolver=resolver
    )
    actual_start = resolver.previous_working_day(required)
    successor = Activity("S", 2, actual_start=actual_start, remaining_duration=1)

    assert classify_out_of_sequence(
        successor,
        relationship_required_start=required,
        data_date=date(2026, 10, 2),
    ) is OutOfSequenceState.OUT_OF_SEQUENCE
    assert resolve_out_of_sequence_action(
        successor,
        relationship_required_start=required,
        data_date=date(2026, 10, 2),
        mode=mode,
    ) is expected_action


def test_oos_reference_matrix_is_deterministic():
    from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
    from construction_pm.scheduling.forward_pass import ScheduledActivity
    from construction_pm.scheduling.out_of_sequence import relationship_required_start
    from construction_pm.scheduling.relationships import Relationship, RelationshipType

    resolver = WorkingTimeResolver(WorkingCalendar())
    predecessor = ScheduledActivity(
        "P", date(2026, 9, 28), date(2026, 9, 30), 2
    )
    snapshots = []
    for relationship_type in RelationshipType:
        relationship = Relationship("P", "S", relationship_type, 0)
        required = relationship_required_start(
            relationship, predecessor, 2, resolver=resolver
        )
        snapshots.append((relationship_type.value, required.isoformat()))
    assert snapshots == [
        ("FS", "2026-10-01"),
        ("SS", "2026-09-28"),
        ("FF", "2026-09-29"),
        ("SF", "2026-09-25"),
    ]


@pytest.mark.parametrize("relationship_type", __import__(
    "construction_pm.scheduling.relationships", fromlist=["RelationshipType"]
).RelationshipType)
@pytest.mark.parametrize("mode", list(OutOfSequenceScheduleType))
def test_oos_reference_matrix_not_started_successor_keeps_logic(relationship_type, mode):
    from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
    from construction_pm.scheduling.forward_pass import ScheduledActivity
    from construction_pm.scheduling.out_of_sequence import relationship_required_start
    from construction_pm.scheduling.relationships import Relationship

    resolver = WorkingTimeResolver(WorkingCalendar())
    predecessor = ScheduledActivity("P", date(2026, 9, 28), date(2026, 9, 30), 2)
    relationship = Relationship("P", "S", relationship_type, 0)
    required = relationship_required_start(relationship, predecessor, 2, resolver=resolver)
    successor = Activity("S", 2)

    assert classify_out_of_sequence(
        successor, relationship_required_start=required, data_date=date(2026, 10, 2)
    ) is OutOfSequenceState.NOT_STARTED
    assert resolve_out_of_sequence_action(
        successor,
        relationship_required_start=required,
        data_date=date(2026, 10, 2),
        mode=mode,
    ) is ProgressRelationAction.APPLY_LOGIC


@pytest.mark.parametrize("relationship_type", __import__(
    "construction_pm.scheduling.relationships", fromlist=["RelationshipType"]
).RelationshipType)
@pytest.mark.parametrize("mode", list(OutOfSequenceScheduleType))
def test_oos_reference_matrix_in_sequence_successor_keeps_logic(relationship_type, mode):
    from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
    from construction_pm.scheduling.forward_pass import ScheduledActivity
    from construction_pm.scheduling.out_of_sequence import relationship_required_start
    from construction_pm.scheduling.relationships import Relationship

    resolver = WorkingTimeResolver(WorkingCalendar())
    predecessor = ScheduledActivity("P", date(2026, 9, 28), date(2026, 9, 30), 2)
    relationship = Relationship("P", "S", relationship_type, 0)
    required = relationship_required_start(relationship, predecessor, 2, resolver=resolver)
    successor = Activity("S", 2, actual_start=required, remaining_duration=1)

    assert classify_out_of_sequence(
        successor, relationship_required_start=required, data_date=date(2026, 10, 2)
    ) is OutOfSequenceState.IN_SEQUENCE
    assert resolve_out_of_sequence_action(
        successor,
        relationship_required_start=required,
        data_date=date(2026, 10, 2),
        mode=mode,
    ) is ProgressRelationAction.APPLY_LOGIC


@pytest.mark.parametrize("relationship_type", __import__(
    "construction_pm.scheduling.relationships", fromlist=["RelationshipType"]
).RelationshipType)
@pytest.mark.parametrize("mode, expected_action", [
    (OutOfSequenceScheduleType.RETAINED_LOGIC, ProgressRelationAction.APPLY_LOGIC),
    (OutOfSequenceScheduleType.PROGRESS_OVERRIDE, ProgressRelationAction.IGNORE_LOGIC),
    (OutOfSequenceScheduleType.ACTUAL_DATES, ProgressRelationAction.USE_ACTUAL_DATES),
])
def test_oos_reference_matrix_completed_successor_preserves_progress_boundary(
    relationship_type, mode, expected_action
):
    from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
    from construction_pm.scheduling.forward_pass import ScheduledActivity
    from construction_pm.scheduling.out_of_sequence import relationship_required_start
    from construction_pm.scheduling.relationships import Relationship

    resolver = WorkingTimeResolver(WorkingCalendar())
    predecessor = ScheduledActivity("P", date(2026, 9, 28), date(2026, 9, 30), 2)
    relationship = Relationship("P", "S", relationship_type, 0)
    required = relationship_required_start(relationship, predecessor, 2, resolver=resolver)
    actual_start = resolver.previous_working_day(required)
    successor = Activity(
        "S", 2, actual_start=actual_start, actual_finish=actual_start, remaining_duration=0
    )

    assert classify_out_of_sequence(
        successor, relationship_required_start=required, data_date=date(2026, 10, 2)
    ) is OutOfSequenceState.OUT_OF_SEQUENCE
    assert resolve_out_of_sequence_action(
        successor,
        relationship_required_start=required,
        data_date=date(2026, 10, 2),
        mode=mode,
    ) is expected_action


@pytest.mark.parametrize("relationship_type", list(RelationshipType))
@pytest.mark.parametrize(
    ("mode", "expected_start"),
    [
        (OutOfSequenceScheduleType.RETAINED_LOGIC, None),
        (OutOfSequenceScheduleType.PROGRESS_OVERRIDE, date(2026, 10, 2)),
        (OutOfSequenceScheduleType.ACTUAL_DATES, None),
    ],
)
def test_schedule_applies_oos_mode_to_in_progress_successor(
    relationship_type, mode, expected_start
):
    resolver = WorkingTimeResolver(WorkingCalendar())
    predecessor = Activity("P", 2)
    probe = Activity("S", 1)
    from construction_pm.scheduling.forward_pass import forward_pass

    baseline = forward_pass(
        [predecessor, probe],
        [Relationship("P", "S", relationship_type)],
        date(2026, 9, 21),
        resolver,
    )
    required_start = baseline["S"].start
    actual_start = resolver.previous_working_day(required_start)
    successor = Activity(
        "S",
        2,
        actual_start=actual_start,
        remaining_duration=1,
    )
    result = schedule(
        [predecessor, successor],
        [Relationship("P", "S", relationship_type)],
        date(2026, 9, 21),
        resolver,
        project_finish=date(2026, 10, 5),
        options=ScheduleOptions(
            data_date=date(2026, 10, 2),
            out_of_sequence_schedule_type=mode,
        ),
    )

    assert result.early_activities is not None
    if expected_start is not None:
        assert result.early_activities["S"].start == expected_start
        assert result.early_activities["S"].duration == 1
    else:
        assert result.early_activities["S"].start == required_start
        assert result.early_activities["S"].duration == 1


@pytest.mark.parametrize("relationship_type", list(RelationshipType))
def test_schedule_actual_dates_uses_actual_dates_for_completed_oos_activity(relationship_type):
    resolver = WorkingTimeResolver(WorkingCalendar())
    predecessor = Activity("P", 2)
    probe = Activity("S", 1)
    from construction_pm.scheduling.forward_pass import forward_pass

    baseline = forward_pass(
        [predecessor, probe],
        [Relationship("P", "S", relationship_type)],
        date(2026, 9, 21),
        resolver,
    )
    required_start = baseline["S"].start
    actual_start = resolver.previous_working_day(required_start)
    activity = Activity(
        "S",
        1,
        actual_start=actual_start,
        actual_finish=actual_start,
        remaining_duration=0,
    )
    result = schedule(
        [predecessor, activity],
        [Relationship("P", "S", relationship_type)],
        date(2026, 9, 21),
        resolver,
        project_finish=date(2026, 10, 5),
        options=ScheduleOptions(
            data_date=date(2026, 10, 2),
            out_of_sequence_schedule_type=OutOfSequenceScheduleType.ACTUAL_DATES,
        ),
    )

    assert result.early_activities is not None
    assert result.early_activities["S"].start == actual_start
    assert result.early_activities["S"].finish == actual_start
    assert result.early_activities["S"].duration == 0


def test_schedule_respects_in_sequence_actual_start_for_root_activity():
    resolver = WorkingTimeResolver(WorkingCalendar())
    result = schedule(
        [Activity("A", 1, actual_start=date(2026, 9, 24), remaining_duration=1)],
        [],
        date(2026, 9, 21),
        resolver,
    )
    assert result.early_activities is not None
    assert result.early_activities["A"].start == date(2026, 9, 24)


def test_schedule_requires_data_date_only_when_progress_is_confirmed_out_of_sequence():
    resolver = WorkingTimeResolver(WorkingCalendar())
    result = schedule(
        [Activity("P", 2), Activity("S", 1, actual_start=date(2026, 9, 23), remaining_duration=1)],
        [Relationship("P", "S", RelationshipType.FS)],
        date(2026, 9, 21),
        resolver,
    )
    assert result.early_activities is not None
    assert result.early_activities["S"].start == date(2026, 9, 23)
