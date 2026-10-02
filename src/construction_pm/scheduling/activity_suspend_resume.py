from __future__ import annotations

from datetime import datetime


class ActivitySuspendResumeError(ValueError):
    """Raised when P6 suspend/resume date semantics are invalid."""


def validate_activity_suspend_resume(
    *,
    actual_start: datetime | None,
    actual_finish: datetime | None,
    suspend_date: datetime | None,
    resume_date: datetime | None,
) -> None:
    """Validate Oracle P6 Activity suspend/resume ordering semantics.

    Suspend/resume is intentionally kept outside the date-only CPM Activity
    model until the scheduler can consume the time-aware interval directly.
    """

    if suspend_date is None and resume_date is not None:
        raise ActivitySuspendResumeError("resume_date requires suspend_date")

    if suspend_date is not None:
        if actual_start is None:
            raise ActivitySuspendResumeError("suspend_date requires actual_start")
        if suspend_date <= actual_start:
            raise ActivitySuspendResumeError(
                "suspend_date must be later than actual_start"
            )

    if resume_date is not None:
        if resume_date <= suspend_date:
            raise ActivitySuspendResumeError(
                "resume_date must be later than suspend_date"
            )
        if actual_finish is None:
            raise ActivitySuspendResumeError(
                "resume_date requires actual_finish for P6 ordering validation"
            )
        if resume_date >= actual_finish:
            raise ActivitySuspendResumeError(
                "resume_date must be earlier than actual_finish"
            )
