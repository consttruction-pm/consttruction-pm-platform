from datetime import date
from decimal import Decimal

import pytest

from construction_pm.scheduling import (
    CalendarSystem,
    JalaliDate,
    WorkingCalendar,
    WorkingTimeResolver,
)


def test_jalali_input_is_converted_to_canonical_gregorian_date():
    calendar = WorkingCalendar.from_calendar_dates(
        system=CalendarSystem.JALALI,
        holidays=[JalaliDate(1405, 7, 8)],
    )
    resolver = WorkingTimeResolver(calendar)
    assert resolver.is_working_day(JalaliDate(1405, 7, 7))
    assert not resolver.is_working_day(JalaliDate(1405, 7, 8))
    assert resolver.normalize_start(JalaliDate(1405, 7, 8)) == date(2026, 10, 1)


def test_jalali_holiday_is_skipped_during_addition_and_subtraction():
    calendar = WorkingCalendar.from_calendar_dates(
        system=CalendarSystem.JALALI,
        holidays=[JalaliDate(1405, 7, 8)],
    )
    resolver = WorkingTimeResolver(calendar)
    assert resolver.add_working_duration(JalaliDate(1405, 7, 7), 2) == date(2026, 10, 1)
    assert resolver.subtract_working_duration(JalaliDate(1405, 7, 9), 2) == date(2026, 9, 29)


def test_jalali_duration_matches_gregorian_duration():
    calendar = WorkingCalendar.from_calendar_dates(system=CalendarSystem.JALALI)
    resolver = WorkingTimeResolver(calendar)
    assert resolver.calculate_duration(JalaliDate(1405, 7, 6), JalaliDate(1405, 7, 8)) == 3
    assert resolver.calculate_duration(date(2026, 9, 28), date(2026, 9, 30)) == 3


def test_gregorian_calendar_rejects_jalali_input():
    resolver = WorkingTimeResolver(WorkingCalendar())
    with pytest.raises(ValueError):
        resolver.normalize_start(JalaliDate(1405, 7, 8))


def test_jalali_and_gregorian_resolvers_produce_identical_working_day_arithmetic():
    jalali = WorkingCalendar.from_calendar_dates(
        system=CalendarSystem.JALALI,
        holidays=[JalaliDate(1405, 7, 8)],
    )
    gregorian = WorkingCalendar(
        holidays=frozenset({date(2026, 9, 30)}),
    )
    jalali_resolver = WorkingTimeResolver(jalali)
    gregorian_resolver = WorkingTimeResolver(gregorian)

    assert jalali_resolver.add_working_duration(JalaliDate(1405, 7, 7), 3) == date(2026, 10, 2)
    assert gregorian_resolver.add_working_duration(date(2026, 9, 29), 3) == date(2026, 10, 2)
    assert jalali_resolver.calculate_duration(
        JalaliDate(1405, 7, 7), JalaliDate(1405, 7, 10)
    ) == gregorian_resolver.calculate_duration(date(2026, 9, 29), date(2026, 10, 2))


def test_zero_day_duration_normalizes_to_the_next_working_day_without_consuming_a_day():
    resolver = WorkingTimeResolver(WorkingCalendar())
    assert resolver.add_working_duration(date(2026, 9, 26), 0) == date(2026, 9, 28)


def test_large_day_duration_round_trips_without_fixed_horizon():
    resolver = WorkingTimeResolver(WorkingCalendar())
    start = date(2026, 9, 28)
    finish = resolver.add_working_duration(start, 20000)
    assert resolver.subtract_working_duration(finish, 20000) == start


def test_month_and_year_boundaries_preserve_working_day_count():
    resolver = WorkingTimeResolver(WorkingCalendar())
    assert resolver.calculate_duration(date(2026, 12, 31), date(2027, 1, 1)) == 2
    assert resolver.calculate_duration(date(2026, 3, 20), date(2026, 3, 23)) == 2


def test_p6_calendar_time_period_factors_are_explicit_metadata():
    from construction_pm.scheduling import CalendarTimePeriodFactors

    factors = CalendarTimePeriodFactors("8", 40, "176", 2112)
    assert factors.hours_per_day == Decimal("8")
    assert factors.hours_per_week == Decimal("40")
    assert factors.hours_per_month == Decimal("176")
    assert factors.hours_per_year == Decimal("2112")
    assert factors.value_for("Month") == Decimal("176")
    assert factors.as_p6_fields()["HoursPerYear"] == Decimal("2112")


def test_p6_calendar_time_period_factors_reject_invalid_values():
    from construction_pm.scheduling import CalendarTimePeriodFactors

    with pytest.raises(ValueError, match="hours_per_day"):
        CalendarTimePeriodFactors(hours_per_day=0)
    with pytest.raises(ValueError, match="unsupported calendar time period"):
        CalendarTimePeriodFactors().value_for("quarter")


def test_working_calendar_exposes_time_period_factors_without_changing_day_arithmetic():
    from construction_pm.scheduling import CalendarTimePeriodFactors

    calendar = WorkingCalendar(
        time_period_factors=CalendarTimePeriodFactors(hours_per_day=10, hours_per_week=50),
    )
    resolver = WorkingTimeResolver(calendar)
    assert calendar.hours_per_day == Decimal("10")
    assert calendar.hours_per_week == Decimal("50")
    assert resolver.add_working_duration(date(2026, 10, 5), 2) == date(2026, 10, 6)


def test_working_calendar_canonical_snapshot_is_deterministic_and_round_trips():
    from construction_pm.scheduling import CalendarTimePeriodFactors

    calendar = WorkingCalendar(
        working_weekdays=frozenset({6, 0, 2, 4}),
        holidays=frozenset({date(2026, 10, 2), date(2026, 9, 30)}),
        system=CalendarSystem.JALALI,
        time_period_factors=CalendarTimePeriodFactors(
            hours_per_day="7.5",
            hours_per_week="37.5",
            hours_per_month="165",
            hours_per_year="1980",
        ),
    )

    snapshot = calendar.canonical_snapshot()
    assert snapshot == {
        "system": "jalali",
        "working_weekdays": [0, 2, 4, 6],
        "holidays": ["2026-09-30", "2026-10-02"],
        "time_period_factors": {
            "hours_per_day": "7.5",
            "hours_per_week": "37.5",
            "hours_per_month": "165",
            "hours_per_year": "1980",
        },
    }

    restored = WorkingCalendar.from_canonical_snapshot(snapshot)
    assert restored.canonical_snapshot() == snapshot
    assert restored.is_working_day(date(2026, 10, 5)) == calendar.is_working_day(date(2026, 10, 5))
    assert restored.hours_per_day == Decimal("7.5")


def test_working_calendar_canonical_snapshot_rejects_missing_period_factors():
    snapshot = WorkingCalendar().canonical_snapshot()
    del snapshot["time_period_factors"]["hours_per_year"]
    with pytest.raises(ValueError, match="invalid calendar snapshot"):
        WorkingCalendar.from_canonical_snapshot(snapshot)
