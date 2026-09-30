from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class CalendarSystem(str, Enum):
    GREGORIAN = "gregorian"
    JALALI = "jalali"


class CalendarDateError(ValueError):
    """Raised when a calendar date is outside the supported domain."""


_JALALI_BREAKS = (
    -61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181,
    1210, 1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178,
)


def _div(a: int, b: int) -> int:
    """Integer division truncated toward zero, matching Borkowski's algorithm."""
    if b <= 0:
        raise ValueError("divisor must be positive")
    return a // b if a >= 0 else -((-a) // b)


def _mod(a: int, b: int) -> int:
    """Non-negative modulo, matching the reference algorithm."""
    return a - _div(a, b) * b


def _jalali_cal(year: int) -> tuple[int, int, int, int]:
    if year < _JALALI_BREAKS[0] or year >= _JALALI_BREAKS[-1]:
        raise CalendarDateError("Jalali year is outside the supported conversion range")

    gy = year + 621
    leap_j = -14
    jp = _JALALI_BREAKS[0]
    jump = 0

    for jm in _JALALI_BREAKS[1:]:
        jump = jm - jp
        if year < jm:
            break
        leap_j += _div(jump, 33) * 8 + _div(_mod(jump, 33), 4)
        jp = jm

    n = year - jp
    leap_j += _div(n, 33) * 8 + _div(_mod(n, 33) + 3, 4)
    if _mod(jump, 33) == 4 and jump - n == 4:
        leap_j += 1

    leap_g = _div(gy, 4) - _div((_div(gy, 100) + 1) * 3, 4) - 150
    march = 20 + leap_j - leap_g

    adjusted = n
    if jump - n < 6:
        adjusted = n - jump + _div(jump + 4, 33) * 33
    leap = _mod(_mod(adjusted + 1, 33) - 1, 4)
    if leap == -1:
        leap = 4

    return gy, march, leap, jump


def _is_jalali_leap_year(year: int) -> bool:
    return _jalali_cal(year)[2] == 0


def _jalaali_month_length(year: int, month: int) -> int:
    if month <= 6:
        return 31
    if month <= 11:
        return 30
    return 30 if _is_jalali_leap_year(year) else 29


@dataclass(frozen=True, order=True)
class JalaliDate:
    """Proleptic Persian/Jalali date with deterministic Gregorian conversion."""

    year: int
    month: int
    day: int

    def __post_init__(self) -> None:
        if self.year < 1 or not 1 <= self.month <= 12:
            raise CalendarDateError("invalid Jalali date")
        if not 1 <= self.day <= _jalaali_month_length(self.year, self.month):
            raise CalendarDateError("invalid Jalali date")

    def to_gregorian(self) -> date:
        return jalali_to_gregorian(self.year, self.month, self.day)

    @classmethod
    def from_gregorian(cls, value: date) -> "JalaliDate":
        year, month, day = gregorian_to_jalali(value)
        return cls(year, month, day)


def jalali_to_gregorian(year: int, month: int, day: int) -> date:
    """Convert a Jalali date to Gregorian using the Borkowski cycle and JDN arithmetic."""

    if year < 1:
        raise CalendarDateError("Jalali year must be positive")
    if month < 1 or month > 12 or day < 1 or day > _jalaali_month_length(year, month):
        raise CalendarDateError("invalid Jalali date")

    gy, march, _, _ = _jalali_cal(year)
    jdn = (
        _gregorian_to_borkowski_jdn(gy, 3, march)
        + (month - 1) * 31
        - _div(month, 7) * (month - 7)
        + day - 1
    )
    return _borkowski_jdn_to_gregorian(jdn)


def gregorian_to_jalali(value: date) -> tuple[int, int, int]:
    """Convert a Gregorian date to Jalali using Borkowski JDN arithmetic."""

    jdn = _gregorian_to_borkowski_jdn(value.year, value.month, value.day)
    candidate_year = value.year - 621
    first_day = jalali_to_jdn(candidate_year, 1, 1)

    if jdn < first_day:
        candidate_year -= 1
        first_day = jalali_to_jdn(candidate_year, 1, 1)

    k = jdn - first_day
    if k <= 185:
        return candidate_year, 1 + _div(k, 31), _mod(k, 31) + 1
    k -= 186
    return candidate_year, 7 + _div(k, 30), _mod(k, 30) + 1


def jalali_to_jdn(year: int, month: int, day: int) -> int:
    """Return the Borkowski Julian Day number for a valid Jalali date."""
    gy, march, _, _ = _jalali_cal(year)
    if not 1 <= month <= 12 or not 1 <= day <= _jalaali_month_length(year, month):
        raise CalendarDateError("invalid Jalali date")
    return (
        _gregorian_to_borkowski_jdn(gy, 3, march)
        + (month - 1) * 31
        - _div(month, 7) * (month - 7)
        + day - 1
    )


def _gregorian_to_borkowski_jdn(year: int, month: int, day: int) -> int:
    value = (
        _div((year + _div(month - 8, 6) + 100100) * 1461, 4)
        + _div(153 * _mod(month + 9, 12) + 2, 5)
        + day
        - 34840408
    )
    return value - _div(_div(year + 100100 + _div(month - 8, 6), 100) * 3, 4) + 752


def _borkowski_jdn_to_gregorian(jdn: int) -> date:
    j = 4 * jdn + 139361631
    j += _div(_div(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908
    i = _div(_mod(j, 1461), 4) * 5 + 308
    day = _div(_mod(i, 153), 5) + 1
    month = _mod(_div(i, 153), 12) + 1
    year = _div(j, 1461) - 100100 + _div(8 - month, 6)
    return date(year, month, day)
