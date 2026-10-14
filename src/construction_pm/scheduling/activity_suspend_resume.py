from __future__ import annotations

from datetime import date, datetime
from typing import TypeAlias


ActivityDate: TypeAlias = date | datetime


class ActivitySuspendResumeError(ValueError):
    """Raised when suspend/resume date semantics are invalid."""


def _date_kind(value: ActivityDate) -> type[date] | type[datetime]:
    return datetime if isinstance(value, datetime) else date


def validate_activity_suspend_resume(
    *,
    actual_start: ActivityDate | None,
    actual_finish: ActivityDate | None,
    suspend_date: ActivityDate | None,
    resume_date: ActivityDate | None,
) -> None:
    """Validate suspend/resume ordering for date-based and time-aware inputs.

    The caller must supply all non-null values at the same date/time precision.
    P6 suspend/resume boundaries occur at the beginning of the specified day;
    this validator checks ordering but does not perform schedule calculations.
    """
    values = (actual_start, actual_finish, suspend_date, resume_date)
    if any(value is not None and not isinstance(value, (date, datetime)) for value in values):
        raise ActivitySuspendResumeError("suspend/resume values must be dates or datetimes")
    kinds = {_date_kind(value) for value in values if value is not None}
    if len(kinds) > 1:
        raise ActivitySuspendResumeError("suspend/resume values must use the same date precision")

    if suspend_date is None and resume_date is not None:
        raise ActivitySuspendResumeError("resume_date requires suspend_date")
    if suspend_date is not None:
        if actual_start is None:
            raise ActivitySuspendResumeError("suspend_date requires actual_start")
        if suspend_date <= actual_start:
            raise ActivitySuspendResumeError("suspend_date must be later than actual_start")
    if resume_date is not None:
        if suspend_date is None:
            raise ActivitySuspendResumeError("resume_date requires suspend_date")
        if resume_date <= suspend_date:
            raise ActivitySuspendResumeError("resume_date must be later than suspend_date")
        if actual_finish is not None and resume_date >= actual_finish:
            raise ActivitySuspendResumeError("resume_date must be earlier than actual_finish")
