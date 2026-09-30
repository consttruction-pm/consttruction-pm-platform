from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class CalendarSystem(str, Enum):
    GREGORIAN = "gregorian"
    JALALI = "jalali"


class CalendarDateError(ValueError):
    """Raised when a calendar date is outside the supported domain."""


@dataclass(frozen=True, order=True)
class JalaliDate:
    """Proleptic Persian/Jalali date with deterministic Gregorian conversion."""

    year: int
    month: int
    day: int

    def __post_init__(self) -> None:
        if self.year < 1 or not 1 <= self.month <= 12 or self.day < 1:
            raise CalendarDateError("invalid Jalali date")
        converted = jalali_to_gregorian(self.year, self.month, self.day)
        if gregorian_to_jalali(converted) != (self.year, self.month, self.day):
            raise CalendarDateError("invalid Jalali date")

    def to_gregorian(self) -> date:
        return jalali_to_gregorian(self.year, self.month, self.day)

    @classmethod
    def from_gregorian(cls, value: date) -> "JalaliDate":
        year, month, day = gregorian_to_jalali(value)
        return cls(year, month, day)


def _div(a: int, b: int) -> int:
    return a // b


def jalali_to_gregorian(year: int, month: int, day: int) -> date:
    """Convert a Jalali date to Gregorian using JDN arithmetic."""

    if year < 1:
        raise CalendarDateError("Jalali year must be positive")
    if month < 1 or month > 12 or day < 1:
        raise CalendarDateError("invalid Jalali month/day")

    epbase = year - 474 if year >= 0 else year - 473
    epyear = 474 + (epbase % 2820)
    month_days = (month - 1) * 31 if month <= 7 else (month - 1) * 30 + 6
    jdn = (
        day
        + month_days
        + _div(epyear * 682 - 110, 2816)
        + (epyear - 1) * 365
        + _div(epbase, 2820) * 1029983
        + 1948320
    )
    if month == 12 and day == 30 and jalali_to_jdn(year + 1, 1, 1) != jdn + 1:
        raise CalendarDateError("invalid Jalali date")

    result = _jdn_to_gregorian(jdn)
    if gregorian_to_jalali(result) != (year, month, day):
        raise CalendarDateError("invalid Jalali date")
    return result


def gregorian_to_jalali(value: date) -> tuple[int, int, int]:
    """Convert a Gregorian date to a Jalali date using JDN arithmetic."""

    jdn = _gregorian_to_jdn(value)
    depoch = jdn - jalali_to_jdn(475, 1, 1)
    cycle = _div(depoch, 1029983)
    cyear = depoch % 1029983

    if cyear == 1029982:
        ycycle = 2820
    else:
        aux1 = _div(cyear, 366)
        aux2 = cyear % 366
        ycycle = _div(2134 * aux1 + 2816 * aux2 + 2815, 1028522) + aux1 + 1

    year = ycycle + 2820 * cycle + 474
    if year <= 0:
        year -= 1

    # Preserve the canonical 12/30 representation at a leap-year boundary.
    if jalali_to_jdn(year - 1, 12, 30) == jdn:
        return year - 1, 12, 30

    yday = jdn - jalali_to_jdn(year, 1, 1) + 1
    month = _div(yday - 1, 31) + 1 if yday <= 186 else _div(yday - 187, 30) + 7
    day = jdn - jalali_to_jdn(year, month, 1) + 1
    return year, month, day


def jalali_to_jdn(year: int, month: int, day: int) -> int:
    epbase = year - 474 if year >= 0 else year - 473
    epyear = 474 + (epbase % 2820)
    month_days = (month - 1) * 31 if month <= 7 else (month - 1) * 30 + 6
    return (
        day
        + month_days
        + _div(epyear * 682 - 110, 2816)
        + (epyear - 1) * 365
        + _div(epbase, 2820) * 1029983
        + 1948320
    )


def _gregorian_to_jdn(value: date) -> int:
    a = _div(14 - value.month, 12)
    y = value.year + 4800 - a
    m = value.month + 12 * a - 3
    return value.day + _div(153 * m + 2, 5) + 365 * y + _div(y, 4) - _div(y, 100) + _div(y, 400) - 32045


def _jdn_to_gregorian(jdn: int) -> date:
    a = jdn + 32044
    b = _div(4 * a + 3, 146097)
    c = a - _div(146097 * b, 4)
    d = _div(4 * c + 3, 1461)
    e = c - _div(1461 * d, 4)
    m = _div(5 * e + 2, 153)
    day = e - _div(153 * m + 2, 5) + 1
    month = m + 3 - 12 * _div(m, 10)
    year = 100 * b + d - 4800 + _div(m, 10)
    return date(year, month, day)
