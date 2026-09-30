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
