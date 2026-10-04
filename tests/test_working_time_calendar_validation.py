from datetime import date, datetime, time
from decimal import Decimal

import pytest

from construction_pm.scheduling.time_calendar import WorkingTimeCalendar


def test_working_time_calendar_rejects_invalid_weekday_types():
    with pytest.raises(ValueError, match="weekday"):
        WorkingTimeCalendar(working_weekdays=frozenset({True}))


def test_working_time_calendar_rejects_datetime_holidays():
    with pytest.raises(ValueError, match="holidays"):
        WorkingTimeCalendar(holidays=frozenset({datetime(2026, 1, 1)}))


def test_working_time_calendar_rejects_non_mapping_intervals():
    with pytest.raises(ValueError, match="daily_intervals"):
        WorkingTimeCalendar(daily_intervals=())


@pytest.mark.parametrize("intervals", [
    {0: ((8, 17),)},
    {0: ((time(8),),)},
    {0: ((time(8), time(17), time(18)),)},
])
def test_working_time_calendar_rejects_malformed_intervals(intervals):
    with pytest.raises(ValueError, match="working interval"):
        WorkingTimeCalendar(daily_intervals=intervals)


def test_working_time_calendar_accepts_valid_intervals():
    calendar = WorkingTimeCalendar(
        working_weekdays=frozenset({0}),
        holidays=frozenset({date(2026, 1, 1)}),
        daily_intervals={0: ((time(8), time(12)), (time(13), time(17)))},
    )
    assert calendar.intervals_for(date(2026, 1, 5))



def test_working_time_calendar_daily_intervals_are_immutable():
    calendar = WorkingTimeCalendar(daily_intervals={0: ((time(8), time(17)),)})

    with pytest.raises(TypeError):
        calendar.daily_intervals[0] = ((time(9), time(17)),)

    assert calendar.intervals_for(date(2026, 1, 5)) == ((time(8), time(17)),)
