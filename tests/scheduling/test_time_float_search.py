"""P0-C differential and monotonicity tests for Time-Aware Free Float.

The pre-P0-C implementation probed delays 0, 1, 2, ... up to 9999 and stopped
at the first delay whose relationship event no longer held.  ``_legacy_free_float_limit``
is that exact loop, retained as the oracle.  These tests prove the bounded
search returns the same value for every boundary shape, and they verify the
calendar monotonicity property the search relies on.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import importlib

import pytest
from construction_pm.scheduling.benchmark_fixtures import (
    canonical_hash,
    time_calendar,
    time_network,
    time_schedule_payload,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.time_calendar import TimeAwareWorkingTimeResolver
time_schedule_module = importlib.import_module("construction_pm.scheduling.time_schedule")

from construction_pm.scheduling.time_schedule import (
    _FREE_FLOAT_LINEAR_PREFIX,
    _FREE_FLOAT_SEARCH_CEILING,
    _free_float_limit,
    _legacy_free_float_limit,
)

BOUNDARIES = [
    0,
    1,
    2,
    7,
    _FREE_FLOAT_LINEAR_PREFIX,
    _FREE_FLOAT_LINEAR_PREFIX + 1,
    16,
    17,
    1000,
    9998,
    9999,
    10000,
    20000,
]


def _holds_before(first_false):
    def holds(delay: Decimal) -> bool:
        return first_false is None or delay < Decimal(first_false)

    return holds


@pytest.mark.parametrize("first_false", BOUNDARIES)
def test_bounded_search_matches_legacy_scan_at_every_boundary(first_false):
    holds = _holds_before(first_false)
    assert _free_float_limit(holds) == _legacy_free_float_limit(holds)


@pytest.mark.parametrize("first_false", BOUNDARIES)
def test_search_evaluates_far_fewer_delays_than_the_legacy_scan(first_false):
    legacy_calls = {"count": 0}

    def legacy_holds(delay):
        legacy_calls["count"] += 1
        return _holds_before(first_false)(delay)

    _legacy_free_float_limit(legacy_holds)

    new_calls = {"count": 0}

    def new_holds(delay):
        new_calls["count"] += 1
        return _holds_before(first_false)(delay)

    _free_float_limit(new_holds)
    assert new_calls["count"] < legacy_calls["count"] or legacy_calls["count"] <= _FREE_FLOAT_LINEAR_PREFIX + 2
    assert new_calls["count"] <= 40


def test_sentinel_is_preserved_when_no_boundary_is_found():
    assert _free_float_limit(_holds_before(None)) == Decimal("9999")
    assert _legacy_free_float_limit(_holds_before(None)) == Decimal("9999")


def test_sentinel_is_preserved_when_the_boundary_is_exactly_the_scan_end():
    assert _free_float_limit(_holds_before(int(_FREE_FLOAT_SEARCH_CEILING))) == Decimal("9999")
    assert _free_float_limit(_holds_before(9999)) == Decimal("9998")


def test_zero_and_one_boundaries():
    assert _free_float_limit(_holds_before(0)) == Decimal("0")
    assert _free_float_limit(_holds_before(1)) == Decimal("0")
    assert _free_float_limit(_holds_before(2)) == Decimal("1")


@pytest.mark.parametrize("shape", ["dag", "mixed", "fan", "slack", "wide"])
@pytest.mark.parametrize("float_days", [1, 3])
def test_time_schedule_output_is_identical_when_the_legacy_scan_is_restored(
    monkeypatch, shape, float_days
):
    fixture = time_network(60, shape, seed=11, float_days=float_days)
    bounded = time_schedule_module.time_schedule(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.project_finish,
        fixture.registry,
    )
    monkeypatch.setattr(
        time_schedule_module, "_free_float_limit", time_schedule_module._legacy_free_float_limit
    )
    legacy = time_schedule_module.time_schedule(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.project_finish,
        fixture.registry,
    )
    assert canonical_hash(time_schedule_payload(bounded)) == canonical_hash(
        time_schedule_payload(legacy)
    )


def test_time_resolver_duration_is_monotone_in_the_delay():
    resolver = TimeAwareWorkingTimeResolver(time_calendar())
    start = datetime(2026, 1, 5, 10, tzinfo=timezone.utc)
    values = [resolver.add_working_hours(start, hours) for hours in range(0, 400, 3)]
    assert values == sorted(values)


def test_time_resolver_duration_is_monotone_across_a_holiday():
    calendar = time_calendar()
    resolver = TimeAwareWorkingTimeResolver(calendar)
    start = datetime(2026, 1, 5, 8, tzinfo=timezone.utc)
    values = [resolver.add_working_hours(start, hours) for hours in range(0, 24 * 4)]
    assert values == sorted(values)
    assert all(value.date() != date(2026, 1, 6) for value in values if value.date() != start.date())


def test_lag_arithmetic_is_monotone_for_positive_and_negative_lags():
    resolver = TimeAwareWorkingTimeResolver(time_calendar())
    events = [
        datetime(2026, 1, 5, 8, tzinfo=timezone.utc) + timedelta(hours=step)
        for step in range(0, 200, 2)
    ]
    for lag in (Decimal("0"), Decimal("8"), Decimal("-8"), Decimal("24"), Decimal("-24")):
        results = [
            resolver.add_working_hours(event, lag)
            if lag >= 0
            else resolver.subtract_working_hours(event, -lag)
            for event in events
        ]
        assert results == sorted(results)


def test_working_day_arithmetic_is_monotone_with_holidays():
    resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({date(2026, 1, 6), date(2026, 2, 17)}))
    )
    start = date(2026, 1, 5)
    values = [resolver.add_working_duration(start, days) for days in range(0, 200)]
    assert values == sorted(values)


def test_slack_network_has_large_free_float_on_the_short_activities():
    fixture = time_network(40, "slack", seed=3, float_days=60)
    result = time_schedule_module.time_schedule(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.project_finish,
        fixture.registry,
    )
    free_floats = sorted(
        float_item.free_float_value for float_item in result.floats.values()
    )
    assert free_floats[-1] > Decimal("300")
