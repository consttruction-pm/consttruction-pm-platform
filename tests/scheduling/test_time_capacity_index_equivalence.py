"""Differential proof for the P0-L time-capacity day index.

Every arithmetic method of :class:`TimeAwareWorkingTimeResolver` was rewritten
so that whole non-working days are skipped using a cached per-interval capacity
profile instead of walking each day's intervals. The pre-change implementation
is kept here verbatim as an independent oracle.

The checks cover calendars with one or many daily intervals, breaks,
microsecond boundaries, holidays, weekend-only weeks, Jalali-system metadata,
naive/UTC/fixed-offset/DST time zones, exception overlays (local and inherited)
and cursor placements on every boundary. Values, ``Decimal`` results, exception
types and messages are compared, and one end-to-end schedule runs the real
forward pass, backward pass and float pass against the oracle resolver so the
observable scheduling result (FS/SS/FF/SF, signed lags, early/late dates, total
and free float, critical path) is proven identical.
"""

from __future__ import annotations

import hashlib
import json
import pickle
import random
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
    RelationshipLagCalendar,
    SchedulingCalendarContext,
)
from construction_pm.scheduling.calendar_exception_overlay import (
    CalendarExceptionLayers,
    ExceptionAwareWorkingTimeCalendar,
)
from construction_pm.scheduling.calendar_exceptions import (
    CalendarException,
    CalendarExceptionType,
)
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_calendar import (
    TimeAwareWorkingTimeResolver,
    WorkingTimeCalendar,
)
from construction_pm.scheduling.time_duration import LagQuantity, TimeQuantity
from construction_pm.scheduling.time_forward_pass import TimeActivity, TimeRelationship
from construction_pm.scheduling.time_schedule import time_schedule


# --------------------------------------------------------------------------
# Oracle: the exact pre-change implementation, retained as the reference.
# --------------------------------------------------------------------------


def _td_microseconds(value: timedelta) -> int:
    return value.days * 86_400_000_000 + value.seconds * 1_000_000 + value.microseconds


def _oracle_duration_microseconds(value: Decimal | int | float, *, unit: str) -> int:
    """Pre-change duration conversion (Decimal-only, no integer fast path)."""
    units = Decimal(str(value))
    if not units.is_finite() or units < 0:
        raise ValueError(f"{unit} must be a finite non-negative value")
    microseconds = units * Decimal("3600000000")
    if microseconds != microseconds.to_integral_value():
        raise ValueError(f"{unit} is more precise than one microsecond")
    return int(microseconds)


def _oracle_combine(value_date: date, value_time: time, reference: datetime) -> datetime:
    return datetime.combine(value_date, value_time, tzinfo=reference.tzinfo)


class OracleTimeResolver:
    """Pre-change time-aware resolver used only as an equality oracle."""

    def __init__(self, calendar) -> None:
        self.calendar = calendar

    @staticmethod
    def _require_datetime(value, *, field: str) -> datetime:
        if not isinstance(value, datetime):
            raise TypeError(f"{field} must be a datetime")
        return value

    def intervals_for(self, value: date):
        return self.calendar.intervals_for(value)

    def normalize_start(self, value: datetime) -> datetime:
        value = self._require_datetime(value, field="value")
        cursor = value
        while True:
            intervals = self.intervals_for(cursor.date())
            for start, end in intervals:
                if cursor.time() < start:
                    return _oracle_combine(cursor.date(), start, cursor)
                if start <= cursor.time() < end:
                    return cursor
            cursor = _oracle_combine(cursor.date() + timedelta(days=1), time.min, cursor)

    def normalize_finish(self, value: datetime) -> datetime:
        value = self._require_datetime(value, field="value")
        cursor = value
        while True:
            intervals = self.intervals_for(cursor.date())
            for start, end in reversed(intervals):
                if cursor.time() >= end:
                    return _oracle_combine(cursor.date(), end, cursor)
                if start <= cursor.time() < end:
                    return cursor
            cursor = _oracle_combine(cursor.date() - timedelta(days=1), time.max, cursor)

    def add_working_hours(self, start: datetime, hours) -> datetime:
        start = self._require_datetime(start, field="start")
        remaining_microseconds = _oracle_duration_microseconds(hours, unit="hours")
        cursor = self.normalize_start(start)
        while True:
            intervals = self.intervals_for(cursor.date())
            for interval_start, interval_end in intervals:
                begin = _oracle_combine(cursor.date(), interval_start, cursor)
                end = _oracle_combine(cursor.date(), interval_end, cursor)
                if cursor < begin:
                    cursor = begin
                if not (begin <= cursor < end):
                    continue

                capacity_microseconds = _td_microseconds(end - cursor)
                if remaining_microseconds <= capacity_microseconds:
                    return cursor + timedelta(microseconds=remaining_microseconds)
                remaining_microseconds -= capacity_microseconds
                cursor = end

            cursor = _oracle_combine(cursor.date() + timedelta(days=1), time.min, cursor)

    def subtract_working_hours(self, finish: datetime, hours) -> datetime:
        finish = self._require_datetime(finish, field="finish")
        remaining_microseconds = _oracle_duration_microseconds(hours, unit="hours")
        cursor = self.normalize_finish(finish)
        while True:
            intervals = self.intervals_for(cursor.date())
            for interval_start, interval_end in reversed(intervals):
                begin = _oracle_combine(cursor.date(), interval_start, cursor)
                end = _oracle_combine(cursor.date(), interval_end, cursor)
                if cursor >= end:
                    cursor = end
                if not (begin < cursor <= end):
                    continue

                capacity_microseconds = _td_microseconds(cursor - begin)
                if remaining_microseconds <= capacity_microseconds:
                    return cursor - timedelta(microseconds=remaining_microseconds)
                remaining_microseconds -= capacity_microseconds
                cursor = begin

            cursor = _oracle_combine(cursor.date() - timedelta(days=1), time.max, cursor)

    def calculate_working_hours(self, start: datetime, finish: datetime) -> Decimal:
        start = self._require_datetime(start, field="start")
        finish = self._require_datetime(finish, field="finish")
        if finish < start:
            raise ValueError("finish must not precede start")

        total = Decimal("0")
        cursor_date = start.date()
        last_date = finish.date()
        while cursor_date <= last_date:
            for interval_start, interval_end in self.intervals_for(cursor_date):
                begin = _oracle_combine(cursor_date, interval_start, start)
                end = _oracle_combine(cursor_date, interval_end, start)
                left = max(start, begin)
                right = min(finish, end)
                if right > left:
                    total += Decimal(_td_microseconds(right - left)) / Decimal("3600000000")
            cursor_date += timedelta(days=1)
        return total


class OracleBackedTimeResolver(TimeAwareWorkingTimeResolver):
    """Resolver identity required by the registry, arithmetic from the oracle."""

    def __init__(self, calendar) -> None:
        super().__init__(calendar)
        self._oracle = OracleTimeResolver(calendar)

    def normalize_start(self, value):
        return self._oracle.normalize_start(value)

    def normalize_finish(self, value):
        return self._oracle.normalize_finish(value)

    def add_working_hours(self, start, hours):
        return self._oracle.add_working_hours(start, hours)

    def subtract_working_hours(self, finish, hours):
        return self._oracle.subtract_working_hours(finish, hours)

    def calculate_working_hours(self, start, finish):
        return self._oracle.calculate_working_hours(start, finish)


# --------------------------------------------------------------------------
# Calendars and zones
# --------------------------------------------------------------------------

SPLIT = ((time(8, 0), time(12, 0)), (time(13, 0), time(17, 0)))
DENSE = (
    (time(6, 0), time(6, 45)),
    (time(7, 0), time(11, 15, 30, 500_000)),
    (time(12, 0), time(15, 45)),
    (time(16, 0), time(19, 0)),
    (time(20, 0), time(23, 59, 59, 999_999)),
)
SINGLE = ((time(9, 0), time(17, 30, 15, 250_000)),)
BRIDGE = ((time(1, 0), time(4, 0)), (time(8, 0), time(17, 0)))
NIGHT = ((time(0, 30), time(2, 30)), (time(9, 0), time(17, 0)))

HOLIDAYS = frozenset(
    {
        date(2026, 9, 23),
        date(2026, 12, 25),
        date(2026, 12, 26),
        date(2027, 1, 1),
        date(2026, 3, 9),  # Monday after the New York spring-forward weekend
        date(2026, 11, 2),  # Monday after the New York fall-back weekend
    }
)


def _weekday_calendar(intervals, holidays=HOLIDAYS, **kwargs) -> WorkingTimeCalendar:
    return WorkingTimeCalendar(
        holidays=holidays,
        daily_intervals={weekday: intervals for weekday in range(5)},
        **kwargs,
    )


CALENDARS = {
    "split": _weekday_calendar(SPLIT),
    "dense": _weekday_calendar(DENSE),
    "single": _weekday_calendar(SINGLE),
    "bridge": _weekday_calendar(BRIDGE),
    "night": _weekday_calendar(NIGHT),
    "seven-day": WorkingTimeCalendar(
        working_weekdays=frozenset(range(7)),
        holidays=frozenset({date(2026, 3, 8), date(2026, 11, 1)}),
        daily_intervals={weekday: SPLIT for weekday in range(7)},
    ),
    "weekend": WorkingTimeCalendar(
        working_weekdays=frozenset({5, 6}),
        holidays=frozenset({date(2026, 3, 7), date(2026, 11, 7)}),
        daily_intervals={5: ((time(10, 0), time(14, 0)),), 6: ((time(10, 0), time(14, 0)),)},
    ),
    "jalali-system": _weekday_calendar(SPLIT, system=CalendarSystem.JALALI),
}

ZONES = {
    "naive": None,
    "utc": timezone.utc,
    "fixed+0330": timezone(timedelta(hours=3, minutes=30)),
    "new-york": ZoneInfo("America/New_York"),
    "london": ZoneInfo("Europe/London"),
}

PROBE_TIMES = [
    time(0, 0),
    time(0, 0, 0, 1),
    time(1, 0),
    time(1, 30),
    time(2, 30),
    time(3, 0),
    time(5, 59, 59, 999_999),
    time(6, 0),
    time(7, 31),
    time(8, 0),
    time(11, 59, 59, 999_999),
    time(12, 0),
    time(12, 30),
    time(13, 0),
    time(16, 59, 59),
    time(17, 0),
    time(19, 0),
    time(23, 59, 59, 999_999),
]

PROBE_DATES = [
    *[date(2026, 3, day) for day in range(6, 11)],  # New York / London spring DST
    *[date(2026, 10, day) for day in range(29, 32)],  # London fall-back window
    *[date(2026, 11, day) for day in range(1, 4)],  # New York fall-back window
    *[date(2026, 3, day) for day in range(27, 32)],
    *[date(2026, 9, day) for day in range(21, 26)],
    *[date(2026, 12, day) for day in range(24, 32)],
    *[date(2027, 1, day) for day in range(1, 3)],
]

DURATIONS = [0, 1, Decimal("1.5"), 8, Decimal("8.75"), 40]


def _probes(zone) -> list[datetime]:
    return [
        datetime.combine(value, probe_time, tzinfo=zone)
        for value in PROBE_DATES
        for probe_time in PROBE_TIMES
    ]


def _resolvers(calendar) -> tuple[TimeAwareWorkingTimeResolver, OracleTimeResolver]:
    return TimeAwareWorkingTimeResolver(calendar), OracleTimeResolver(calendar)


def _call(function, *args):
    try:
        return ("ok", function(*args))
    except BaseException as exc:  # noqa: BLE001 - exceptions are compared
        return ("raise", type(exc), str(exc))


def _assert_same(function_name: str, optimized, oracle, *args) -> None:
    expected = _call(getattr(oracle, function_name), *args)
    actual = _call(getattr(optimized, function_name), *args)
    assert actual == expected, f"{function_name}{args}"


# --------------------------------------------------------------------------
# Arithmetic equivalence
# --------------------------------------------------------------------------


@pytest.mark.parametrize("calendar_name", sorted(CALENDARS))
@pytest.mark.parametrize("zone_name", ["naive", "new-york", "fixed+0330"])
def test_every_operation_matches_the_verbatim_oracle(calendar_name, zone_name):
    calendar = CALENDARS[calendar_name]
    optimized, oracle = _resolvers(calendar)
    probes = _probes(ZONES[zone_name])

    for probe in probes:
        _assert_same("normalize_start", optimized, oracle, probe)
        _assert_same("normalize_finish", optimized, oracle, probe)
        for hours in DURATIONS:
            _assert_same("add_working_hours", optimized, oracle, probe, hours)
            _assert_same("subtract_working_hours", optimized, oracle, probe, hours)


@pytest.mark.parametrize("calendar_name", ["split", "dense", "night"])
@pytest.mark.parametrize("zone_name", ["utc", "london"])
def test_utc_and_london_zones_match_the_verbatim_oracle(calendar_name, zone_name):
    calendar = CALENDARS[calendar_name]
    optimized, oracle = _resolvers(calendar)
    probes = _probes(ZONES[zone_name])[::3]
    for probe in probes:
        _assert_same("normalize_start", optimized, oracle, probe)
        _assert_same("normalize_finish", optimized, oracle, probe)
        for hours in (0, Decimal("2.5"), 24):
            _assert_same("add_working_hours", optimized, oracle, probe, hours)
            _assert_same("subtract_working_hours", optimized, oracle, probe, hours)


@pytest.mark.parametrize("calendar_name", ["split", "dense", "weekend"])
@pytest.mark.parametrize("zone_name", ["naive", "new-york", "fixed+0330"])
def test_large_durations_match_the_verbatim_oracle(calendar_name, zone_name):
    calendar = CALENDARS[calendar_name]
    optimized, oracle = _resolvers(calendar)
    probes = _probes(ZONES[zone_name])[::11]
    for probe in probes:
        for hours in (Decimal("123.5"), 260 * 8, 2000):
            _assert_same("add_working_hours", optimized, oracle, probe, hours)
            _assert_same("subtract_working_hours", optimized, oracle, probe, hours)


@pytest.mark.parametrize("calendar_name", ["split", "bridge", "dense"])
@pytest.mark.parametrize("zone_name", ["naive", "new-york", "london", "fixed+0330"])
def test_calculate_working_hours_matches_the_verbatim_oracle(calendar_name, zone_name):
    calendar = CALENDARS[calendar_name]
    optimized, oracle = _resolvers(calendar)
    probes = _probes(ZONES[zone_name])
    rng = random.Random(20261118)

    pairs = []
    for index, first in enumerate(probes[::9]):
        for offset in (0, 1, 2, 4):
            if index + offset < len(probes):
                pairs.append((first, probes[index + offset]))
        pairs.append((first, first))
    for _ in range(60):
        start_index = rng.randrange(len(probes))
        pairs.append((probes[start_index], probes[min(len(probes) - 1, start_index + rng.randrange(30))]))

    for start, finish in pairs:
        _assert_same("calculate_working_hours", optimized, oracle, start, finish)
        _assert_same("calculate_working_hours", optimized, oracle, finish, start)


def test_calculate_working_hours_mixed_zones_matches_the_oracle():
    calendar = CALENDARS["split"]
    optimized, oracle = _resolvers(calendar)
    new_york = ZoneInfo("America/New_York")
    tokyo = ZoneInfo("Asia/Tokyo")
    pairs = [
        (datetime(2026, 3, 6, 9, tzinfo=new_york), datetime(2026, 3, 12, 10, tzinfo=tokyo)),
        (datetime(2026, 3, 6, 9, tzinfo=tokyo), datetime(2026, 3, 12, 10, tzinfo=new_york)),
        (datetime(2026, 11, 1, 23, 30, tzinfo=new_york), datetime(2026, 11, 2, 0, 30, tzinfo=tokyo)),
        (datetime(2026, 9, 22, 10), datetime(2026, 9, 24, 10, tzinfo=timezone.utc)),
        (datetime(2026, 9, 22, 10, tzinfo=timezone.utc), datetime(2026, 9, 24, 10)),
        (datetime(2026, 12, 24, 9, tzinfo=new_york), datetime(2027, 1, 5, 16, tzinfo=tokyo)),
        (datetime(2026, 12, 31, 23, 30, tzinfo=tokyo), datetime(2027, 1, 1, 0, 30, tzinfo=new_york)),
    ]
    for start, finish in pairs:
        _assert_same("calculate_working_hours", optimized, oracle, start, finish)
        _assert_same("calculate_working_hours", optimized, oracle, finish, start)


def test_capacity_profile_equals_the_measured_interval_elapsed_times():
    """The cached profile must be the exact sum the day loop would measure."""
    for calendar_name, calendar in CALENDARS.items():
        for zone_name, zone in ZONES.items():
            resolver = TimeAwareWorkingTimeResolver(calendar)
            for probe_date in (
                *[date(2026, 1, 1) + timedelta(days=offset) for offset in range(0, 400, 3)],
                date(2026, 3, 8),
                date(2026, 11, 1),
                date(2026, 3, 29),
                date(2026, 10, 25),
            ):
                profile = resolver._capacity_for(probe_date)
                intervals = calendar.intervals_for(probe_date)
                assert profile.intervals == intervals
                expected = tuple(
                    max(
                        0,
                        _td_microseconds(
                            datetime.combine(probe_date, end, tzinfo=zone)
                            - datetime.combine(probe_date, start, tzinfo=zone)
                        ),
                    )
                    for start, end in intervals
                )
                assert profile.capacities == expected, (calendar_name, zone_name, probe_date)
                assert profile.total == sum(expected)


def test_capacity_cache_size_is_bounded_by_distinct_interval_shapes():
    resolver = TimeAwareWorkingTimeResolver(CALENDARS["split"])
    start = datetime(2026, 1, 1, 9)
    for offset in range(0, 1200):
        resolver.add_working_hours(start + timedelta(days=offset), 3)
    # Weekday shapes (plus the shape of any exception date) are shared by every
    # date, so a float search spanning years cannot grow the table with the span.
    assert len(resolver._capacity) <= 4


# --------------------------------------------------------------------------
# Exceptions and inheritance overlays
# --------------------------------------------------------------------------


EXCEPTION_CASES = {
    "nonwork": (date(2026, 9, 22), CalendarExceptionType.NONWORK, None, ()),
    "detailed": (
        date(2026, 9, 22),
        CalendarExceptionType.DETAILED_WORK_HOURS,
        None,
        ((time(10, 0), time(11, 15)), (time(13, 30), time(14, 0))),
    ),
    "total": (date(2026, 9, 22), CalendarExceptionType.TOTAL_WORK_HOURS, Decimal("4.25"), ()),
    "reset-on-holiday": (date(2026, 9, 23), CalendarExceptionType.RESET_TO_STANDARD, None, ()),
    "detailed-on-holiday": (
        date(2026, 12, 25),
        CalendarExceptionType.DETAILED_WORK_HOURS,
        None,
        ((time(9, 0), time(10, 30)),),
    ),
    "total-on-holiday": (date(2026, 12, 26), CalendarExceptionType.TOTAL_WORK_HOURS, Decimal("2"), ()),
    "reset": (date(2026, 3, 8), CalendarExceptionType.RESET_TO_STANDARD, None, ()),
}

EXCEPTION_PROBE_DATES = [
    *[date(2026, 9, day) for day in range(21, 26)],
    *[date(2026, 12, day) for day in range(24, 29)],
    *[date(2027, 1, day) for day in range(1, 3)],
    *[date(2026, 3, day) for day in range(6, 11)],
]


def _exception(name: str) -> CalendarException:
    value, kind, total, intervals = EXCEPTION_CASES[name]
    return CalendarException(date=value, kind=kind, total_work_hours=total, intervals=intervals)


@pytest.mark.parametrize("case_name", sorted(EXCEPTION_CASES))
@pytest.mark.parametrize("zone_name", ["naive", "new-york", "fixed+0330"])
def test_local_exception_overlay_matches_the_oracle(case_name, zone_name):
    base = CALENDARS["split"]
    calendar = ExceptionAwareWorkingTimeCalendar(base, CalendarExceptionLayers(local=(_exception(case_name),)))
    optimized, oracle = _resolvers(calendar)
    probes = [
        datetime.combine(value, probe_time, tzinfo=ZONES[zone_name])
        for value in EXCEPTION_PROBE_DATES
        for probe_time in PROBE_TIMES[::3]
    ]
    for probe in probes:
        _assert_same("normalize_start", optimized, oracle, probe)
        _assert_same("normalize_finish", optimized, oracle, probe)
        for hours in (0, 1, Decimal("2.5"), 8, 24, Decimal("60.5")):
            _assert_same("add_working_hours", optimized, oracle, probe, hours)
            _assert_same("subtract_working_hours", optimized, oracle, probe, hours)
    rng = random.Random(77)
    for _ in range(40):
        index = rng.randrange(len(probes))
        finish_index = min(len(probes) - 1, index + rng.randrange(12))
        _assert_same(
            "calculate_working_hours", optimized, oracle, probes[index], probes[finish_index]
        )


def test_inherited_exception_layers_match_the_oracle():
    base = CALENDARS["split"]
    layers = CalendarExceptionLayers(
        local=(CalendarException(date=date(2026, 9, 22), kind=CalendarExceptionType.NONWORK),),
        inherited=(
            CalendarException(
                date=date(2026, 9, 23),
                kind=CalendarExceptionType.DETAILED_WORK_HOURS,
                intervals=((time(9, 0), time(11, 0)),),
            ),
            CalendarException(
                date=date(2026, 9, 24),
                kind=CalendarExceptionType.TOTAL_WORK_HOURS,
                total_work_hours=Decimal("3"),
            ),
        ),
    )
    optimized, oracle = _resolvers(ExceptionAwareWorkingTimeCalendar(base, layers))
    for zone in (None, ZoneInfo("America/New_York")):
        for probe in (
            datetime(2026, 9, 21, 9, tzinfo=zone),
            datetime(2026, 9, 22, 9, tzinfo=zone),
            datetime(2026, 9, 23, 9, tzinfo=zone),
            datetime(2026, 9, 24, 9, tzinfo=zone),
            datetime(2026, 9, 25, 9, tzinfo=zone),
        ):
            _assert_same("normalize_start", optimized, oracle, probe)
            _assert_same("normalize_finish", optimized, oracle, probe)
            for hours in (0, 1, Decimal("3.5"), 40):
                _assert_same("add_working_hours", optimized, oracle, probe, hours)
                _assert_same("subtract_working_hours", optimized, oracle, probe, hours)
        for hours in (Decimal("0.5"), Decimal("7.25"), 24):
            _assert_same(
                "add_working_hours", optimized, oracle, datetime(2026, 9, 21, 9, tzinfo=zone), hours
            )
        _assert_same(
            "calculate_working_hours",
            optimized,
            oracle,
            datetime(2026, 9, 21, 9, tzinfo=zone),
            datetime(2026, 9, 25, 9, tzinfo=zone),
        )


# --------------------------------------------------------------------------
# Boundaries, validation and overflow
# --------------------------------------------------------------------------


def test_overflow_past_the_maximum_date_matches_the_oracle():
    optimized, oracle = _resolvers(CALENDARS["split"])
    start = datetime(9999, 12, 29, 9)
    for hours in (1, 8, 40, 200):
        _assert_same("add_working_hours", optimized, oracle, start, hours)
    finish = datetime(1, 1, 3, 9)
    for hours in (1, 8, 40, 200):
        _assert_same("subtract_working_hours", optimized, oracle, finish, hours)


def test_invalid_durations_and_dates_raise_the_same_errors():
    optimized, oracle = _resolvers(CALENDARS["split"])
    probe = datetime(2026, 9, 22, 9)
    for hours in (
        -1,
        Decimal("-0.5"),
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("0.0000000001"),
        True,
        "8",
        None,
    ):
        _assert_same("add_working_hours", optimized, oracle, probe, hours)
        _assert_same("subtract_working_hours", optimized, oracle, probe, hours)
    for bad in (date(2026, 9, 22), "2026-09-22", None):
        _assert_same("add_working_hours", optimized, oracle, bad, 1)
        _assert_same("subtract_working_hours", optimized, oracle, bad, 1)
        _assert_same("normalize_start", optimized, oracle, bad)
        _assert_same("normalize_finish", optimized, oracle, bad)


def test_zero_and_fractional_cursors_round_trip_like_the_oracle():
    optimized, oracle = _resolvers(CALENDARS["bridge"])
    zone = ZoneInfo("America/New_York")
    for probe_date in (date(2026, 3, 6), date(2026, 3, 8), date(2026, 3, 9), date(2026, 11, 1)):
        for probe_time in PROBE_TIMES:
            probe = datetime.combine(probe_date, probe_time, tzinfo=zone)
            for hours in (Decimal("0.1"), Decimal("0.000001"), Decimal("4.999999"), 7):
                added = optimized.add_working_hours(probe, hours)
                assert added == oracle.add_working_hours(probe, hours)
                _assert_same("subtract_working_hours", optimized, oracle, added, hours)


def test_pickled_resolver_reproduces_every_result():
    optimized, _ = _resolvers(CALENDARS["split"])
    restored = pickle.loads(pickle.dumps(optimized))
    reference = TimeAwareWorkingTimeResolver(CALENDARS["split"])
    for probe in (
        datetime(2026, 3, 6, 9),
        datetime(2026, 3, 9, 9),
        datetime(2026, 11, 2, 9),
        datetime(2026, 12, 25, 9),
    ):
        assert restored.add_working_hours(probe, 30) == reference.add_working_hours(probe, 30)
        assert restored.subtract_working_hours(probe, 30) == reference.subtract_working_hours(probe, 30)
        assert restored.calculate_working_hours(
            probe, probe + timedelta(days=20)
        ) == reference.calculate_working_hours(probe, probe + timedelta(days=20))


# --------------------------------------------------------------------------
# End-to-end schedule: forward, backward and float passes on oracle arithmetic
# --------------------------------------------------------------------------


def _schedule_fixture():
    site = WorkingTimeCalendar(
        holidays=frozenset({date(2026, 9, 23), date(2026, 10, 12), date(2026, 12, 25)}),
        daily_intervals={weekday: SPLIT for weekday in range(5)},
    )
    night = WorkingTimeCalendar(
        holidays=frozenset({date(2026, 10, 5)}),
        daily_intervals={weekday: NIGHT for weekday in range(5)},
    )
    site_ref = CalendarReference("site", "1", "working-time")
    night_ref = CalendarReference("night", "1", "working-time")
    context = SchedulingCalendarContext(project=site_ref, activity=site_ref, relationship_lag=site_ref)
    night_context = SchedulingCalendarContext(project=site_ref, activity=night_ref, relationship_lag=site_ref)

    activities = tuple(
        TimeActivity(
            f"a{index:02d}",
            TimeQuantity.working_hours(((index % 4) + 1) * 8 + (4 if index % 7 == 3 else 0)),
            night_context if index % 5 == 2 else context,
        )
        for index in range(24)
    )

    types = (
        RelationshipType.FS,
        RelationshipType.SS,
        RelationshipType.FF,
        RelationshipType.SF,
    )
    lag_hours = (0, 8, -8, 16)
    relationships = []
    edge = 0
    for chain in range(3):
        for step in range(7):
            predecessor = chain * 8 + step
            successor = predecessor + 1
            relationships.append(
                TimeRelationship(
                    f"a{predecessor:02d}",
                    f"a{successor:02d}",
                    types[edge % len(types)],
                    LagQuantity.working_hours(Decimal(lag_hours[edge % len(lag_hours)])),
                )
            )
            edge += 1
        if chain < 2:
            relationships.append(
                TimeRelationship(
                    f"a{chain * 8 + 7:02d}",
                    f"a{(chain + 1) * 8:02d}",
                    types[edge % len(types)],
                    LagQuantity.working_hours(Decimal(lag_hours[edge % len(lag_hours)])),
                )
            )
        edge += 1
    relationships.append(
        TimeRelationship("a00", "a17", RelationshipType.SS, LagQuantity.working_hours(Decimal("-4")))
    )

    layers = {
        "site@1": CalendarExceptionLayers(
            local=(
                CalendarException(date=date(2026, 9, 30), kind=CalendarExceptionType.NONWORK),
                CalendarException(
                    date=date(2026, 9, 16),
                    kind=CalendarExceptionType.DETAILED_WORK_HOURS,
                    intervals=((time(10, 0), time(12, 0)), (time(14, 0), time(16, 0))),
                ),
            )
        )
    }
    return site, night, activities, tuple(relationships), layers


def _registry(site, night, layers, *, oracle: bool) -> CalendarResolverRegistry:
    factory = OracleBackedTimeResolver if oracle else TimeAwareWorkingTimeResolver
    return CalendarResolverRegistry(
        time_resolvers={"site@1": factory(site), "night@1": factory(night)},
        exception_layers=layers,
    )


def _fingerprint(result) -> tuple[str, dict[str, tuple]]:
    floats: dict[str, tuple] = {}
    for activity_id in sorted(result.floats):
        item = result.floats[activity_id]
        floats[activity_id] = (
            item.early_start.isoformat(),
            item.early_finish.isoformat(),
            item.late_start.isoformat(),
            item.late_finish.isoformat(),
            item.total_float_hours,
            item.free_float_hours,
            item.total_float_value,
            item.free_float_value,
            item.critical,
        )
    payload = {
        "project_finish": result.project_finish.isoformat(),
        "floats": {key: [str(value) for value in values] for key, values in floats.items()},
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return digest, floats


def test_time_schedule_matches_the_oracle_engine_end_to_end():
    site, night, activities, relationships, layers = _schedule_fixture()
    start = datetime(2026, 9, 1, 8)
    options_kwargs = {"relationship_lag_calendar": RelationshipLagCalendar.SUCCESSOR}

    from construction_pm.scheduling.time_schedule import TimeScheduleOptions

    options = TimeScheduleOptions(**options_kwargs)
    optimized = time_schedule(
        activities, relationships, start, None, _registry(site, night, layers, oracle=False), options=options
    )
    oracle = time_schedule(
        activities, relationships, start, None, _registry(site, night, layers, oracle=True), options=options
    )

    optimized_digest, optimized_floats = _fingerprint(optimized)
    oracle_digest, oracle_floats = _fingerprint(oracle)
    assert optimized_digest == oracle_digest
    assert optimized_floats == oracle_floats
    assert optimized.project_finish == oracle.project_finish
    assert set(optimized.early_activities) == set(oracle.early_activities)
    for activity_id in optimized.early_activities:
        assert optimized.early_activities[activity_id] == oracle.early_activities[activity_id]
        assert optimized.late_activities[activity_id] == oracle.late_activities[activity_id]

    # Worker count is execution-only: the same fixture under two workers keeps
    # the sequential mapping byte for byte.
    parallel = time_schedule(
        activities,
        relationships,
        start,
        None,
        _registry(site, night, layers, oracle=False),
        options=options,
        float_workers=2,
    )
    assert _fingerprint(parallel) == (optimized_digest, optimized_floats)


# --------------------------------------------------------------------------
# Registry memoisation
# --------------------------------------------------------------------------


def _registry_with_exception() -> CalendarResolverRegistry:
    layers = CalendarExceptionLayers(
        local=(CalendarException(date=date(2026, 9, 22), kind=CalendarExceptionType.NONWORK),)
    )
    return CalendarResolverRegistry(
        time_resolvers={"cal@v1": TimeAwareWorkingTimeResolver(CALENDARS["split"])},
        exception_layers={"cal@v1": layers},
    )


def test_registry_resolve_returns_one_validated_view_per_reference():
    registry = _registry_with_exception()
    first = registry.resolve(CalendarReference("cal", "v1", "working-time"))
    second = registry.resolve(CalendarReference("cal", "v1", "working-time"))
    assert first is second
    assert isinstance(first.calendar, ExceptionAwareWorkingTimeCalendar)

    fresh = _registry_with_exception().resolve(CalendarReference("cal", "v1", "working-time"))
    assert fresh is not first
    probe = datetime(2026, 9, 22, 9)
    for hours in (1, 8, 24):
        assert first.add_working_hours(probe, hours) == fresh.add_working_hours(probe, hours)
        assert first.subtract_working_hours(probe, hours) == fresh.subtract_working_hours(probe, hours)
    assert first.calculate_working_hours(
        probe, datetime(2026, 9, 30, 9)
    ) == fresh.calculate_working_hours(probe, datetime(2026, 9, 30, 9))


def test_registry_cache_is_keyed_by_calendar_version():
    """A different pinned version is a different schedule input, never a hit."""
    v1 = _weekday_calendar(SPLIT, holidays=frozenset({date(2026, 9, 22)}))
    v2 = _weekday_calendar(SPLIT, holidays=frozenset({date(2026, 9, 23)}))
    registry = CalendarResolverRegistry(
        time_resolvers={
            "cal@2026.01": TimeAwareWorkingTimeResolver(v1),
            "cal@2026.02": TimeAwareWorkingTimeResolver(v2),
        }
    )
    first = registry.resolve(CalendarReference("cal", "2026.01", "working-time"))
    second = registry.resolve(CalendarReference("cal", "2026.02", "working-time"))
    assert first is not second
    # Each version keeps its own holidays: 2026-09-22 is non-working in v1 and
    # working in v2, and vice versa for 2026-09-23.
    assert first.normalize_start(datetime(2026, 9, 22, 9)) == datetime(2026, 9, 23, 8)
    assert second.normalize_start(datetime(2026, 9, 22, 9)) == datetime(2026, 9, 22, 9)
    assert second.normalize_start(datetime(2026, 9, 23, 9)) == datetime(2026, 9, 24, 8)


def test_registry_still_raises_on_every_invalid_reference_after_caching():
    registry = _registry_with_exception()
    good = CalendarReference("cal", "v1", "working-time")
    assert registry.resolve(good) is registry.resolve(good)

    for bad in (
        CalendarReference("missing", "v1", "working-time"),
        CalendarReference("cal", "v2", "working-time"),
        CalendarReference("cal", "v1", "working-day"),
    ):
        for _ in range(2):
            with pytest.raises((KeyError, ValueError)):
                registry.resolve(bad)
    for _ in range(2):
        with pytest.raises(ValueError):
            registry.resolve(CalendarReference("cal", "v1", "working-time", CalendarSystem.JALALI))
    assert registry.resolve(good) is registry.resolve(good)


def test_registry_reports_inheritance_cycles_on_every_call():
    registry = CalendarResolverRegistry(
        time_resolvers={"a@1": TimeAwareWorkingTimeResolver(CALENDARS["split"])},
        base_calendar_references={"a@1": CalendarReference("a", "1", "working-time")},
    )
    for _ in range(3):
        with pytest.raises(ValueError, match="CALENDAR_INHERITANCE_CYCLE"):
            registry.resolve(CalendarReference("a", "1", "working-time"))


def test_registry_rejects_unregistered_parent_reference_on_every_call():
    registry = CalendarResolverRegistry(
        time_resolvers={
            "child@1": TimeAwareWorkingTimeResolver(CALENDARS["split"]),
            "parent@1": TimeAwareWorkingTimeResolver(CALENDARS["split"]),
        },
        base_calendar_references={"child@1": CalendarReference("parent", "2", "working-time")},
    )
    for _ in range(3):
        with pytest.raises(KeyError):
            registry.resolve(CalendarReference("child", "1", "working-time"))
