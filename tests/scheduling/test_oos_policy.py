from datetime import date

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.out_of_sequence import OutOfSequenceState, ProgressRelationAction
from construction_pm.scheduling.progress_state import resolve_progress_state
from construction_pm.scheduling.schedule_options import OutOfSequenceScheduleType
from construction_pm.scheduling.oos_policy import resolve_oos_policy


def test_progress_override_ignores_relationship_but_preserves_progress_state():
    resolver = WorkingTimeResolver(WorkingCalendar())
    activity = Activity(
        "S", 5, actual_start=date(2026, 9, 24), remaining_duration=2
    )
    progress = resolve_progress_state(activity, resolver=resolver, data_date=date(2026, 9, 30))
    result = resolve_oos_policy(
        activity, progress,
        relationship_required_start=date(2026, 9, 28),
        data_date=date(2026, 9, 30),
        mode=OutOfSequenceScheduleType.PROGRESS_OVERRIDE,
    )
    assert result.state is OutOfSequenceState.OUT_OF_SEQUENCE
    assert result.action is ProgressRelationAction.IGNORE_LOGIC
    assert result.apply_relationship_logic is False
    assert result.preserve_actual_dates is True
    assert result.preserve_remaining_work is True
    assert progress.remaining.remaining_duration == 2


def test_actual_dates_keeps_relationship_from_rescheduling_progressed_work():
    resolver = WorkingTimeResolver(WorkingCalendar())
    activity = Activity(
        "S", 5, actual_start=date(2026, 9, 24), remaining_duration=2
    )
    progress = resolve_progress_state(activity, resolver=resolver, data_date=date(2026, 9, 30))
    result = resolve_oos_policy(
        activity, progress,
        relationship_required_start=date(2026, 9, 28),
        data_date=date(2026, 9, 30),
        mode=OutOfSequenceScheduleType.ACTUAL_DATES,
    )
    assert result.action is ProgressRelationAction.USE_ACTUAL_DATES
    assert result.apply_relationship_logic is False
    assert result.preserve_actual_dates is True
    assert result.preserve_remaining_work is True


def test_retained_logic_applies_relationship_and_preserves_progress():
    resolver = WorkingTimeResolver(WorkingCalendar())
    activity = Activity(
        "S", 5, actual_start=date(2026, 9, 24), remaining_duration=2
    )
    progress = resolve_progress_state(activity, resolver=resolver, data_date=date(2026, 9, 30))
    result = resolve_oos_policy(
        activity, progress,
        relationship_required_start=date(2026, 9, 28),
        data_date=date(2026, 9, 30),
        mode=OutOfSequenceScheduleType.RETAINED_LOGIC,
    )
    assert result.action is ProgressRelationAction.APPLY_LOGIC
    assert result.apply_relationship_logic is True
    assert result.preserve_actual_dates is True
    assert result.preserve_remaining_work is True


def test_completed_activity_is_not_rescheduled_by_oos_policy():
    resolver = WorkingTimeResolver(WorkingCalendar())
    activity = Activity(
        "S", 5,
        actual_start=date(2026, 9, 24),
        actual_finish=date(2026, 9, 25),
        remaining_duration=0,
    )
    progress = resolve_progress_state(activity, resolver=resolver)
    result = resolve_oos_policy(
        activity, progress,
        relationship_required_start=date(2026, 9, 28),
        data_date=date(2026, 9, 30),
        mode=OutOfSequenceScheduleType.PROGRESS_OVERRIDE,
    )
    assert progress.state.value == "COMPLETE"
    assert result.preserve_remaining_work is True
