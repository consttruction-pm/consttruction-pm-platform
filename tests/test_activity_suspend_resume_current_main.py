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
