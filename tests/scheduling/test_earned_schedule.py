from datetime import date
from decimal import Decimal

import pytest

from construction_pm.scheduling.calendar_system import JalaliDate
from construction_pm.scheduling.earned_schedule import (
    EarnedScheduleError,
    EarnedSchedulePeriod,
    calculate_earned_schedule,
)


def periods():
    return (
        EarnedSchedulePeriod(date(2026, 1, 31), Decimal("100")),
        EarnedSchedulePeriod(date(2026, 2, 28), Decimal("200")),
        EarnedSchedulePeriod(date(2026, 3, 31), Decimal("300")),
        EarnedSchedulePeriod(date(2026, 4, 30), Decimal("400")),
    )


def test_on_time_es_and_spi_t():
    result = calculate_earned_schedule(
        periods(), earned_value=200, data_date=date(2026, 2, 28), project_start=date(2026, 1, 1)
    )
    assert result.earned_schedule == Decimal("58")
    assert result.actual_time == Decimal("58")
    assert result.time_unit == "calendar-day"
    assert result.spi_t == Decimal("1")
    assert result.sv_t == Decimal("0")
    assert result.status == "ON_TIME"


def test_ahead_of_schedule():
    result = calculate_earned_schedule(
        periods(), earned_value=250, data_date=date(2026, 3, 15), project_start=date(2026, 1, 1)
    )
    assert result.earned_schedule == Decimal("74")
    assert result.status == "AHEAD"
    assert result.spi_t > Decimal("1")


def test_behind_schedule():
    result = calculate_earned_schedule(
        periods(), earned_value=150, data_date=date(2026, 3, 31), project_start=date(2026, 1, 1)
    )
    assert result.earned_schedule == Decimal("30")
    assert result.status == "BEHIND"
    assert result.spi_t < Decimal("1")


def test_zero_ev_is_supported_when_pv_exists():
    result = calculate_earned_schedule(
        periods(), earned_value=0, data_date=date(2026, 1, 15), project_start=date(2026, 1, 1)
    )
    assert result.earned_schedule == Decimal("0")


def test_zero_pv_period_does_not_divide_by_zero():
    values = (
        EarnedSchedulePeriod(date(2026, 1, 31), 0),
        EarnedSchedulePeriod(date(2026, 2, 28), 100),
    )
    result = calculate_earned_schedule(
        values, earned_value=50, data_date=date(2026, 2, 28), project_start=date(2026, 1, 1)
    )
    assert result.earned_schedule == Decimal("44")


def test_insufficient_pv_is_explicit():
    with pytest.raises(EarnedScheduleError, match="INSUFFICIENT_PV_COVERAGE"):
        calculate_earned_schedule(
            periods(), earned_value=500, data_date=date(2026, 4, 30), project_start=date(2026, 1, 1)
        )


def test_partial_current_period_has_fractional_actual_time():
    result = calculate_earned_schedule(
        periods(), earned_value=100, data_date=date(2026, 2, 14), project_start=date(2026, 1, 1)
    )
    assert result.actual_time == Decimal("44")


def test_jalali_input_normalizes_to_same_canonical_result():
    gregorian_date = date(2026, 3, 21)
    jalali = JalaliDate.from_gregorian(gregorian_date)
    a = calculate_earned_schedule(
        periods(), earned_value=220, data_date=gregorian_date, project_start=date(2026, 1, 1)
    )
    b = calculate_earned_schedule(
        periods(), earned_value=220, data_date=jalali, project_start=JalaliDate.from_gregorian(date(2026, 1, 1))
    )
    assert b.canonical_snapshot() == a.canonical_snapshot()


def test_reconciliation_is_deterministic():
    result = calculate_earned_schedule(
        periods(), earned_value=200, data_date=date(2026, 2, 28), project_start=date(2026, 1, 1)
    )
    reconciliation = result.reconcile(Decimal("58"))
    assert reconciliation.earned_schedule_progress == Decimal("58")
    assert reconciliation.schedule_progress == Decimal("58")
    assert reconciliation.progress_variance == Decimal("0")
    assert reconciliation.status == "ALIGNED"
