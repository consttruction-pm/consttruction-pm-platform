from datetime import time

import pytest

from construction_pm.scheduling.time_calendar import WorkingTimeCalendar


def test_invalid_working_weekday_is_rejected():
    with pytest.raises(ValueError, match="working weekday must be between 0 and 6"):
        WorkingTimeCalendar(working_weekdays=frozenset({0, 1, 7}))


def test_negative_working_weekday_is_rejected():
    with pytest.raises(ValueError, match="working weekday must be between 0 and 6"):
        WorkingTimeCalendar(working_weekdays=frozenset({-1, 0, 1}))


def test_valid_sunday_working_weekday_remains_supported():
    calendar = WorkingTimeCalendar(
        working_weekdays=frozenset({6}),
        daily_intervals={6: ((time(8), time(12)),)},
    )
    assert calendar.daily_intervals[6] == ((time(8), time(12)),)
