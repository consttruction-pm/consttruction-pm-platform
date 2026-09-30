from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity, PercentCompleteType


def test_activity_accepts_p6_progress_state_inputs():
    activity = Activity(
        "A",
        10,
        actual_start=date(2026, 9, 21),
        remaining_duration=4,
        remaining_start=date(2026, 9, 25),
        percent_complete=60,
        percent_complete_type=PercentCompleteType.DURATION,
        expected_finish=date(2026, 10, 2),
    )

    assert activity.actual_start == date(2026, 9, 21)
    assert activity.remaining_duration == 4
    assert activity.remaining_start == date(2026, 9, 25)
    assert activity.percent_complete == 60
    assert activity.percent_complete_type is PercentCompleteType.DURATION
    assert activity.expected_finish == date(2026, 10, 2)


@pytest.mark.parametrize("percent_type", list(PercentCompleteType))
def test_activity_accepts_each_p6_percent_complete_type(percent_type):
    activity = Activity("A", 10, percent_complete_type=percent_type)
    assert activity.percent_complete_type is percent_type


def test_completed_activity_requires_zero_remaining_duration_and_full_progress():
    activity = Activity(
        "A",
        10,
        actual_start=date(2026, 9, 21),
        actual_finish=date(2026, 10, 2),
        remaining_duration=0,
        percent_complete=100,
    )

    assert activity.actual_finish == date(2026, 10, 2)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"actual_finish": date(2026, 9, 22)},
        {
            "actual_start": date(2026, 9, 23),
            "actual_finish": date(2026, 9, 22),
        },
        {
            "actual_start": date(2026, 9, 21),
            "actual_finish": date(2026, 9, 22),
            "remaining_duration": 1,
        },
        {"remaining_duration": -1},
        {"percent_complete": -1},
        {"percent_complete": 101},
        {"percent_complete_type": "DURATION"},
        {
            "actual_start": date(2026, 9, 21),
            "expected_finish": date(2026, 9, 20),
        },
    ],
)
def test_activity_rejects_invalid_progress_state(kwargs):
    with pytest.raises((ValueError, TypeError)):
        Activity("A", 10, **kwargs)


def test_unstarted_activity_can_omit_progress_state():
    activity = Activity("A", 10)
    assert activity.actual_start is None
    assert activity.actual_finish is None
    assert activity.remaining_duration is None
    assert activity.remaining_start is None
    assert activity.percent_complete is None
    assert activity.expected_finish is None
