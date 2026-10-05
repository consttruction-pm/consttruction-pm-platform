from __future__ import annotations

"""Earned Schedule (ES) and time-based schedule-performance semantics."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Tuple

from .calendar_system import JalaliDate


CalendarDate = date | JalaliDate
_CANONICAL_ZERO = Decimal("0")


class EarnedScheduleError(ValueError):
    """Raised when Earned Schedule cannot be derived safely."""


@dataclass(frozen=True)
class EarnedSchedulePeriod:
    """One cumulative planned-value point on the Earned Schedule time axis."""

    end_date: date
    cumulative_planned_value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.end_date, date) or isinstance(self.end_date, datetime):
            raise TypeError("end_date must be a date")
        value = Decimal(str(self.cumulative_planned_value))
        if not value.is_finite() or value < 0:
            raise ValueError("cumulative_planned_value must be finite and non-negative")
        object.__setattr__(self, "cumulative_planned_value", value)


@dataclass(frozen=True)
class SchedulePerformanceReconciliation:
    """Comparison between Earned Schedule progress and authoritative schedule progress."""

    earned_schedule_progress: Decimal
    schedule_progress: Decimal
    progress_variance: Decimal
    status: str


@dataclass(frozen=True)
class EarnedScheduleResult:
    """Deterministic time-based schedule-performance result."""

    earned_schedule: Decimal
    actual_time: Decimal
    spi_t: Decimal
    sv_t: Decimal
    time_unit: str
    data_date: date
    earned_schedule_date: date | None
    status: str
    cumulative_ev: Decimal
    canonical_period_count: int

    def reconcile(self, authoritative_schedule_time: Decimal, *, tolerance: Decimal = Decimal("0.000000001")) -> SchedulePerformanceReconciliation:
        """Reconcile ES directly against an authoritative network-schedule time."""

        schedule_time = Decimal(str(authoritative_schedule_time))
        tol = Decimal(str(tolerance))
        if not schedule_time.is_finite() or schedule_time < 0:
            raise ValueError("authoritative_schedule_time must be finite and non-negative")
        if not tol.is_finite() or tol < 0:
            raise ValueError("tolerance must be finite and non-negative")
        variance = self.earned_schedule - schedule_time
        if abs(variance) <= tol:
            status = "ALIGNED"
        elif variance > 0:
            status = "EARNED_SCHEDULE_AHEAD"
        else:
            status = "EARNED_SCHEDULE_BEHIND"
        return SchedulePerformanceReconciliation(
            earned_schedule_progress=self.earned_schedule,
            schedule_progress=schedule_time,
            progress_variance=variance,
            status=status,
        )

    def canonical_snapshot(self) -> dict[str, object]:
        return {
            "earned_schedule": str(self.earned_schedule),
            "actual_time": str(self.actual_time),
            "spi_t": str(self.spi_t),
            "sv_t": str(self.sv_t),
            "time_unit": self.time_unit,
            "data_date": self.data_date.isoformat(),
            "earned_schedule_date": (
                self.earned_schedule_date.isoformat() if self.earned_schedule_date else None
            ),
            "status": self.status,
            "cumulative_ev": str(self.cumulative_ev),
            "canonical_period_count": self.canonical_period_count,
        }


def _canonical_date(value: CalendarDate) -> date:
    if isinstance(value, JalaliDate):
        return value.to_gregorian()
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    raise TypeError("calendar date must be date or JalaliDate")


def _validate_periods(periods: Iterable[EarnedSchedulePeriod]) -> Tuple[EarnedSchedulePeriod, ...]:
    ordered = tuple(periods)
    if not ordered:
        raise EarnedScheduleError("NO_SCHEDULE_PERIODS")
    previous_date: date | None = None
    previous_pv = _CANONICAL_ZERO
    for period in ordered:
        if previous_date is not None and period.end_date <= previous_date:
            raise EarnedScheduleError("PERIOD_DATES_MUST_BE_STRICTLY_INCREASING")
        if period.cumulative_planned_value < previous_pv:
            raise EarnedScheduleError("CUMULATIVE_PLANNED_VALUE_MUST_BE_NON_DECREASING")
        previous_date = period.end_date
        previous_pv = period.cumulative_planned_value
    return ordered


def _interpolate_elapsed_days(left: date, right: date, fraction: Decimal) -> Decimal:
    return Decimal((right - left).days) * fraction


def _interpolate_date(left: date, right: date, fraction: Decimal) -> date:
    offset = int(_interpolate_elapsed_days(left, right, fraction).to_integral_value())
    return left.fromordinal(left.toordinal() + offset)


def calculate_earned_schedule(
    periods: Iterable[EarnedSchedulePeriod],
    *,
    earned_value: Decimal | int | float,
    data_date: CalendarDate,
    project_start: CalendarDate,
) -> EarnedScheduleResult:
    """Calculate ES/AT/SPI(t)/SV(t) on an explicit canonical calendar-day axis."""

    ordered = _validate_periods(periods)
    data = _canonical_date(data_date)
    start = _canonical_date(project_start)
    if data < start:
        raise EarnedScheduleError("DATA_DATE_PRECEDES_PROJECT_START")
    if ordered[0].end_date < start:
        raise EarnedScheduleError("PV_PERIOD_PRECEDES_PROJECT_START")

    ev = Decimal(str(earned_value))
    if not ev.is_finite() or ev < 0:
        raise ValueError("earned_value must be finite and non-negative")

    actual_time = Decimal((data - start).days)

    previous_pv = _CANONICAL_ZERO
    previous_date = start
    earned_schedule: Decimal | None = _CANONICAL_ZERO if ev == _CANONICAL_ZERO else None
    earned_schedule_date: date | None = start if ev == _CANONICAL_ZERO else None

    for period in ordered:
        current_pv = period.cumulative_planned_value
        if earned_schedule is None and ev <= current_pv:
            delta = current_pv - previous_pv
            if delta == 0:
                # A flat cumulative-PV segment adds no earned progress.
                # Keep searching for the first positive PV segment so EV=0
                # (or a flat PV plateau) cannot be mapped to its period end.
                previous_pv = current_pv
                previous_date = period.end_date
                continue
            else:
                fraction = (ev - previous_pv) / delta
                if fraction < 0 or fraction > 1:
                    raise EarnedScheduleError("INVALID_PV_AXIS")
                earned_schedule_date = _interpolate_date(previous_date, period.end_date, fraction)
                earned_schedule = (
                    Decimal((previous_date - start).days)
                    + _interpolate_elapsed_days(previous_date, period.end_date, fraction)
                )
            break
        previous_pv = current_pv
        previous_date = period.end_date

    if earned_schedule is None or earned_schedule_date is None:
        raise EarnedScheduleError("INSUFFICIENT_PV_COVERAGE")

    if actual_time == 0:
        spi_t = Decimal("0")
    else:
        spi_t = earned_schedule / actual_time
    sv_t = earned_schedule - actual_time

    if earned_schedule == actual_time:
        status = "ON_TIME"
    elif earned_schedule > actual_time:
        status = "AHEAD"
    else:
        status = "BEHIND"

    return EarnedScheduleResult(
        earned_schedule=earned_schedule,
        actual_time=actual_time,
        spi_t=spi_t,
        sv_t=sv_t,
        time_unit="calendar-day",
        data_date=data,
        earned_schedule_date=earned_schedule_date,
        status=status,
        cumulative_ev=ev,
        canonical_period_count=len(ordered),
    )

__all__ = [
    "EarnedScheduleError",
    "EarnedSchedulePeriod",
    "EarnedScheduleResult",
    "SchedulePerformanceReconciliation",
    "calculate_earned_schedule",
]
