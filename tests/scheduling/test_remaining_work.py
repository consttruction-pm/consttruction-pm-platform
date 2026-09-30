import pytest
from datetime import date

from construction_pm.scheduling.activity import Activity, PercentCompleteType
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.remaining_work import resolve_remaining_work


def test_explicit_remaining_work_wins():
    resolver = WorkingTimeResolver(WorkingCalendar())
    activity = Activity("A", 10, actual_start=date(2026, 9, 21), remaining_duration=4)
    result = resolve_remaining_work(activity, resolver=resolver, data_date=date(2026, 9, 28))
    assert result.remaining_duration == 4
    assert result.remaining_start == date(2026, 9, 28)


def test_duration_percent_complete_derives_remaining_duration():
    resolver = WorkingTimeResolver(WorkingCalendar())
    activity = Activity(
        "A", 10, percent_complete=60, percent_complete_type=PercentCompleteType.DURATION
    )
    result = resolve_remaining_work(activity, resolver=resolver)
    assert result.remaining_duration == 4
    assert result.remaining_start is None


def test_completed_activity_has_no_remaining_work():
    resolver = WorkingTimeResolver(WorkingCalendar())
    activity = Activity(
        "A", 10, actual_start=date(2026, 9, 21), actual_finish=date(2026, 9, 25),
        remaining_duration=0, percent_complete=100,
    )
    assert resolve_remaining_work(activity, resolver=resolver).remaining_duration == 0


def test_remaining_start_is_normalized_to_working_day():
    resolver = WorkingTimeResolver(WorkingCalendar())
    activity = Activity(
        "A", 5, actual_start=date(2026, 9, 25), remaining_duration=3,
        remaining_start=date(2026, 9, 27),
    )
    result = resolve_remaining_work(activity, resolver=resolver)
    assert result.remaining_start == date(2026, 9, 28)


def test_as_of_data_date_estimator_reduces_planned_duration_by_elapsed_work():
    from construction_pm.scheduling.remaining_work import (
        estimate_remaining_work_as_of_data_date,
    )

    resolver = WorkingTimeResolver(WorkingCalendar())
    result = estimate_remaining_work_as_of_data_date(
        Activity("A", 5, actual_start=date(2026, 9, 28)),
        resolver=resolver,
        data_date=date(2026, 9, 30),
    )
    assert result.remaining_duration == 3
    assert result.remaining_start == date(2026, 9, 30)


def test_as_of_data_date_estimator_does_not_override_explicit_remaining():
    resolver = WorkingTimeResolver(WorkingCalendar())
    activity = Activity(
        "A", 5, actual_start=date(2026, 9, 28), remaining_duration=4
    )
    explicit = resolve_remaining_work(
        activity, resolver=resolver, data_date=date(2026, 9, 30)
    )
    assert explicit.remaining_duration == 4


def test_as_of_data_date_rejects_data_date_before_actual_start():
    from construction_pm.scheduling.remaining_work import (
        estimate_remaining_work_as_of_data_date,
    )

    resolver = WorkingTimeResolver(WorkingCalendar())
    with pytest.raises(ValueError, match="must not precede"):
        estimate_remaining_work_as_of_data_date(
            Activity("A", 5, actual_start=date(2026, 9, 28)),
            resolver=resolver,
            data_date=date(2026, 9, 25),
        )
