from datetime import date

import pytest

from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.progress import (
    PercentCompleteType,
    calculate_actual_duration,
    calculate_duration_percent_complete,
    calculate_progress_metrics,
)


@pytest.fixture
def resolver():
    return WorkingTimeResolver(WorkingCalendar())


def test_percent_complete_type_matches_p6_modes():
    assert {item.value for item in PercentCompleteType} == {
        "DURATION",
        "UNITS",
        "PHYSICAL",
        "SCOPE",
    }


@pytest.mark.parametrize(
    ("planned", "remaining", "expected"),
    [
        (10, 10, 0.0),
        (10, 4, 60.0),
        (10, 0, 100.0),
        (0, 0, 100.0),
    ],
)
def test_duration_percent_complete(planned, remaining, expected):
    assert calculate_duration_percent_complete(planned, remaining) == expected


@pytest.mark.parametrize(
    ("planned", "remaining"),
    [
        (-1, 0),
        (10, -1),
        (10, 11),
    ],
)
def test_duration_percent_complete_rejects_invalid_state(planned, remaining):
    with pytest.raises(ValueError):
        calculate_duration_percent_complete(planned, remaining)


def test_actual_duration_uses_working_days_through_data_date(resolver):
    assert calculate_actual_duration(
        date(2026, 9, 21),
        date(2026, 9, 23),
        resolver,
    ) == 2


def test_completed_activity_has_zero_remaining_duration(resolver):
    result = calculate_progress_metrics(
        planned_duration=10,
        remaining_duration=4,
        activity_start=date(2026, 9, 21),
        actual_finish=date(2026, 9, 25),
        data_date=date(2026, 9, 24),
        resolver=resolver,
    )
    assert result.actual_duration == 4
    assert result.remaining_duration == 0
    assert result.duration_percent_complete == 100.0


def test_in_progress_activity_preserves_remaining_duration(resolver):
    result = calculate_progress_metrics(
        planned_duration=10,
        remaining_duration=4,
        activity_start=date(2026, 9, 21),
        actual_finish=None,
        data_date=date(2026, 9, 24),
        resolver=resolver,
    )
    assert result.actual_duration == 3
    assert result.remaining_duration == 4
    assert result.duration_percent_complete == 60.0


def test_unstarted_activity_uses_planned_duration_as_remaining(resolver):
    result = calculate_progress_metrics(
        planned_duration=10,
        remaining_duration=0,
        activity_start=None,
        actual_finish=None,
        data_date=date(2026, 9, 24),
        resolver=resolver,
    )
    assert result.actual_duration == 0
    assert result.remaining_duration == 10
    assert result.duration_percent_complete == 0.0
