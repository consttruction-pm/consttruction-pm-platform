from datetime import datetime

import pytest

from construction_pm.scheduling.activity_suspend_resume import ActivitySuspendResumeError, validate_activity_suspend_resume


def dt(day: int, hour: int = 8) -> datetime:
    return datetime(2026, 10, day, hour)


def test_suspend_requires_actual_start_and_is_later() -> None:
    with pytest.raises(ActivitySuspendResumeError, match="requires actual_start"):
        validate_activity_suspend_resume(actual_start=None, actual_finish=dt(10), suspend_date=dt(7), resume_date=None)
    with pytest.raises(ActivitySuspendResumeError, match="later than actual_start"):
        validate_activity_suspend_resume(actual_start=dt(7), actual_finish=dt(10), suspend_date=dt(7), resume_date=None)


def test_resume_requires_suspend_and_occurs_before_actual_finish() -> None:
    with pytest.raises(ActivitySuspendResumeError, match="requires suspend_date"):
        validate_activity_suspend_resume(actual_start=dt(7), actual_finish=dt(10), suspend_date=None, resume_date=dt(8))
    with pytest.raises(ActivitySuspendResumeError, match="later than suspend_date"):
        validate_activity_suspend_resume(actual_start=dt(7), actual_finish=dt(10), suspend_date=dt(9), resume_date=dt(9))
    with pytest.raises(ActivitySuspendResumeError, match="earlier than actual_finish"):
        validate_activity_suspend_resume(actual_start=dt(7), actual_finish=dt(10), suspend_date=dt(8), resume_date=dt(10))


def test_valid_suspend_resume_order_passes() -> None:
    validate_activity_suspend_resume(actual_start=dt(7), actual_finish=dt(12), suspend_date=dt(8), resume_date=dt(10))


def test_date_based_suspend_resume_uses_beginning_of_day_boundaries() -> None:
    from datetime import date

    from construction_pm.scheduling.activity import Activity, ActivityType

    activity = Activity(
        "A-SUSPENDED",
        3,
        actual_start=date(2026, 10, 1),
        suspend_date=date(2026, 10, 2),
        resume_date=date(2026, 10, 5),
    )
    assert activity.suspend_date == date(2026, 10, 2)
    assert activity.resume_date == date(2026, 10, 5)

    with pytest.raises(ValueError, match="task- or resource-dependent"):
        Activity(
            "A-LOE",
            3,
            actual_start=date(2026, 10, 1),
            activity_type=ActivityType.LEVEL_OF_EFFORT,
            suspend_date=date(2026, 10, 2),
            resume_date=date(2026, 10, 5),
        )


def test_suspend_resume_rejects_mixed_date_precision() -> None:
    from datetime import date

    with pytest.raises(ActivitySuspendResumeError, match="same date precision"):
        validate_activity_suspend_resume(
            actual_start=date(2026, 10, 1),
            actual_finish=None,
            suspend_date=dt(2),
            resume_date=None,
        )
