"""Translate persisted calendar-exception rows into Shared Core exceptions.

The persistence layer stores calendar exceptions as date-keyed records with a
stable mode vocabulary. The scheduling kernel accepts a typed exception object
that is independent of storage. Keeping the translation in one place means a
new persistence adapter or a new composition root cannot silently invent a
different mapping.
"""

from __future__ import annotations

from decimal import Decimal

from .calendar_exception_repository import (
    EXCEPTION_DETAILED_WORK_HOURS,
    EXCEPTION_NONWORK,
    EXCEPTION_RESET_STANDARD,
    EXCEPTION_TOTAL_WORK_HOURS,
    CalendarException as PersistedCalendarException,
)
from .scheduling.calendar_exceptions import (
    CalendarException as KernelCalendarException,
    CalendarExceptionType,
)
from .scheduling.calendar_system import CalendarSystem

_MODE_TO_KIND = {
    EXCEPTION_NONWORK: CalendarExceptionType.NONWORK,
    EXCEPTION_TOTAL_WORK_HOURS: CalendarExceptionType.TOTAL_WORK_HOURS,
    EXCEPTION_DETAILED_WORK_HOURS: CalendarExceptionType.DETAILED_WORK_HOURS,
    EXCEPTION_RESET_STANDARD: CalendarExceptionType.RESET_TO_STANDARD,
}


class CalendarExceptionKernelError(ValueError):
    """Stable error code for a persisted exception the kernel cannot consume."""


def persisted_exception_to_kernel(
    item: PersistedCalendarException,
) -> KernelCalendarException:
    """Convert one persisted record, rejecting unsupported modes explicitly."""

    kind = _MODE_TO_KIND.get(item.mode)
    if kind is None:
        raise CalendarExceptionKernelError("UNSUPPORTED_CALENDAR_EXCEPTION_MODE")
    try:
        # The persisted record always stores the canonical Gregorian date, even
        # when the caller typed a Jalali date. The kernel derives Jalali dates
        # from JalaliDate input only, so the stored canonical date must be
        # declared as Gregorian; the original entry system stays in storage.
        return KernelCalendarException(
            date=item.exception_date,
            kind=kind,
            calendar_system=CalendarSystem.GREGORIAN,
            total_work_hours=(
                None
                if kind is not CalendarExceptionType.TOTAL_WORK_HOURS
                else Decimal(str(item.total_work_hours))
            ),
            intervals=(
                tuple(item.intervals)
                if kind is CalendarExceptionType.DETAILED_WORK_HOURS
                else ()
            ),
        )
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise CalendarExceptionKernelError("INVALID_PERSISTED_CALENDAR_EXCEPTION") from exc


__all__ = ["CalendarExceptionKernelError", "persisted_exception_to_kernel"]
