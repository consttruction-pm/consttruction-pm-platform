from datetime import date

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.progress_state import (
    ActivityProgressState,
    resolve_progress_state,
)


def test_not_started_state_preserves_full_remaining_work():
    resolver = WorkingTimeResolver(WorkingCalendar())
    result = resolve_progress_state(Activity("A", 5), resolver=resolver)
    assert result.state is ActivityProgressState.NOT_STARTED
    assert result.remaining.remaining_duration == 5


def test_started_activity_is_in_progress():
    resolver = WorkingTimeResolver(WorkingCalendar())
    result = resolve_progress_state(
        Activity("A", 5, actual_start=date(2026, 9, 28), remaining_duration=3),
        resolver=resolver,
        data_date=date(2026, 9, 30),
    )
    assert result.state is ActivityProgressState.IN_PROGRESS
    assert result.remaining.remaining_duration == 3


def test_zero_remaining_work_is_complete():
    resolver = WorkingTimeResolver(WorkingCalendar())
    result = resolve_progress_state(
        Activity("A", 5, actual_start=date(2026, 9, 28), remaining_duration=0),
        resolver=resolver,
        data_date=date(2026, 9, 30),
    )
    assert result.state is ActivityProgressState.COMPLETE


def test_actual_finish_is_complete():
    resolver = WorkingTimeResolver(WorkingCalendar())
    result = resolve_progress_state(
        Activity(
            "A", 5,
            actual_start=date(2026, 9, 28),
            actual_finish=date(2026, 10, 2),
            remaining_duration=0,
            percent_complete=100,
        ),
        resolver=resolver,
    )
    assert result.state is ActivityProgressState.COMPLETE
