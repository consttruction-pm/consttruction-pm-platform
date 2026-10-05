from datetime import date, datetime, time
from decimal import Decimal

import pytest

from construction_pm.scheduling.calendar_exceptions import (
    CalendarException,
    CalendarExceptionResolver,
    CalendarExceptionType,
)


TARGET = date(2026, 3, 21)


def test_local_exception_overrides_inherited_exception():
    resolver = CalendarExceptionResolver(standard_is_working=True, standard_total_work_hours=Decimal("8"))
    inherited = CalendarException(TARGET, CalendarExceptionType.NONWORK)
    local = CalendarException(
        TARGET,
        CalendarExceptionType.TOTAL_WORK_HOURS,
        total_work_hours=Decimal("4"),
    )

    result = resolver.resolve(
        TARGET,
        local_exceptions=[local],
        inherited_exceptions=[inherited],
    )

    assert result.source == "local"
    assert result.kind is CalendarExceptionType.TOTAL_WORK_HOURS
    assert result.is_working is True
    assert result.total_work_hours == Decimal("4")


def test_inherited_exception_applies_when_child_has_no_override():
    resolver = CalendarExceptionResolver(standard_is_working=True)
    inherited = CalendarException(TARGET, CalendarExceptionType.NONWORK)

    result = resolver.resolve(TARGET, inherited_exceptions=[inherited])

    assert result.source == "inherited"
    assert result.kind is CalendarExceptionType.NONWORK
    assert result.is_working is False


def test_reset_to_standard_blocks_inherited_exception():
    resolver = CalendarExceptionResolver(
        standard_is_working=True,
        standard_total_work_hours=Decimal("8"),
    )
    inherited = CalendarException(TARGET, CalendarExceptionType.NONWORK)
    local_reset = CalendarException(TARGET, CalendarExceptionType.RESET_TO_STANDARD)

    result = resolver.resolve(
        TARGET,
        local_exceptions=[local_reset],
        inherited_exceptions=[inherited],
    )

    assert result.source == "local"
    assert result.kind is CalendarExceptionType.RESET_TO_STANDARD
    assert result.is_working is True
    assert result.total_work_hours == Decimal("8")


def test_detailed_non_contiguous_override_is_preserved():
    resolver = CalendarExceptionResolver(
        standard_is_working=True,
        standard_intervals=((time(8, 0), time(17, 0)),),
    )
    exception = CalendarException(
        TARGET,
        CalendarExceptionType.DETAILED_WORK_HOURS,
        intervals=((time(8, 0), time(12, 0)), (time(13, 0), time(17, 0))),
    )

    result = resolver.resolve(TARGET, local_exceptions=[exception])

    assert result.is_working is True
    assert result.intervals == (
        (time(8, 0), time(12, 0)),
        (time(13, 0), time(17, 0)),
    )


def test_canonical_snapshot_is_deterministic():
    exception = CalendarException(
        TARGET,
        CalendarExceptionType.TOTAL_WORK_HOURS,
        total_work_hours=Decimal("4.0"),
    )

    assert exception.canonical_snapshot() == {
        "date": "2026-03-21",
        "kind": "TOTAL_WORK_HOURS",
        "total_work_hours": "4.0",
    }


@pytest.mark.parametrize(
    "exception",
    [
        CalendarException(TARGET, CalendarExceptionType.NONWORK),
        CalendarException(TARGET, CalendarExceptionType.RESET_TO_STANDARD),
    ],
)
def test_non_work_or_reset_cannot_carry_hour_payload(exception):
    assert exception.total_work_hours is None
    assert exception.intervals == ()


def test_duplicate_exception_dates_are_rejected():
    resolver = CalendarExceptionResolver(standard_is_working=True)
    values = [
        CalendarException(TARGET, CalendarExceptionType.NONWORK),
        CalendarException(TARGET, CalendarExceptionType.RESET_TO_STANDARD),
    ]

    with pytest.raises(ValueError, match="duplicate calendar exception"):
        resolver.resolve(TARGET, local_exceptions=values)


def test_invalid_total_hours_are_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        CalendarException(
            TARGET,
            CalendarExceptionType.TOTAL_WORK_HOURS,
            total_work_hours=Decimal("-1"),
        )


def test_datetime_is_rejected_at_date_exception_boundaries():
    with pytest.raises(TypeError, match="Gregorian date"):
        CalendarException(datetime(2026, 3, 21, 12, 0), CalendarExceptionType.NONWORK)

    resolver = CalendarExceptionResolver(standard_is_working=True)
    with pytest.raises(TypeError, match="target_date must be a date"):
        resolver.resolve(datetime(2026, 3, 21, 12, 0))
