from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_exception_kernel import (
    CalendarExceptionKernelError,
    persisted_exception_to_kernel,
)
from construction_pm.calendar_exception_repository import CalendarException
from construction_pm.scheduling.calendar_exceptions import CalendarExceptionType
from construction_pm.scheduling.calendar_system import CalendarSystem, JalaliDate

SCOPE = BackendScope("t1", "p1", 0)


def _persisted(**overrides) -> CalendarException:
    values = {
        "scope": SCOPE,
        "calendar_id": "CAL-1",
        "calendar_version": "1",
        "exception_date": date(2026, 10, 20),
        "mode": "nonwork",
    }
    values.update(overrides)
    return CalendarException(**values)


def test_nonwork_and_reset_modes_map_without_payloads() -> None:
    nonwork = persisted_exception_to_kernel(_persisted())
    assert nonwork.kind is CalendarExceptionType.NONWORK
    assert nonwork.date == date(2026, 10, 20)
    assert nonwork.total_work_hours is None
    assert nonwork.intervals == ()

    reset = persisted_exception_to_kernel(_persisted(mode="reset-standard"))
    assert reset.kind is CalendarExceptionType.RESET_TO_STANDARD


def test_total_and_detailed_hours_keep_their_payloads() -> None:
    total = persisted_exception_to_kernel(
        _persisted(mode="total-work-hours", total_work_hours="6.5")
    )
    assert total.kind is CalendarExceptionType.TOTAL_WORK_HOURS
    assert total.total_work_hours == Decimal("6.5")

    detailed = persisted_exception_to_kernel(
        _persisted(
            mode="detailed-work-hours",
            intervals=((time(8, 0), time(12, 0)), (time(13, 0), time(16, 0))),
        )
    )
    assert detailed.kind is CalendarExceptionType.DETAILED_WORK_HOURS
    assert detailed.intervals == ((time(8, 0), time(12, 0)), (time(13, 0), time(16, 0)))


def test_jalali_input_is_canonicalized_to_the_same_gregorian_day() -> None:
    jalali = JalaliDate(1405, 7, 28)
    kernel = persisted_exception_to_kernel(
        _persisted(
            exception_date=jalali,
            system=CalendarSystem.JALALI,
        )
    )
    # Repository persistence canonicalizes the typed Jalali date immediately;
    # the kernel receives that canonical Gregorian day, never a shifted one.
    assert kernel.calendar_system is CalendarSystem.GREGORIAN
    assert kernel.date == jalali.to_gregorian()


def test_unsupported_mode_and_invalid_payload_fail_closed() -> None:
    unsupported = SimpleNamespace(
        mode="unknown-mode",
        exception_date=date(2026, 10, 20),
        system=CalendarSystem.GREGORIAN,
        total_work_hours=None,
        intervals=(),
    )
    with pytest.raises(CalendarExceptionKernelError) as excinfo:
        persisted_exception_to_kernel(unsupported)  # type: ignore[arg-type]
    assert str(excinfo.value) == "UNSUPPORTED_CALENDAR_EXCEPTION_MODE"

    invalid = SimpleNamespace(
        mode="total-work-hours",
        exception_date=date(2026, 10, 20),
        system=CalendarSystem.GREGORIAN,
        total_work_hours=None,
        intervals=(),
    )
    with pytest.raises(CalendarExceptionKernelError) as excinfo:
        persisted_exception_to_kernel(invalid)  # type: ignore[arg-type]
    assert str(excinfo.value) == "INVALID_PERSISTED_CALENDAR_EXCEPTION"
