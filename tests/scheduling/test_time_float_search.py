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
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import LagQuantity
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


# ---------------------------------------------------------------------------
# P0-J: exact interval bound instead of the delay search
# ---------------------------------------------------------------------------


def _time_floats(fixture):
    return time_schedule_module.time_schedule(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.project_finish,
        fixture.registry,
    )


@pytest.mark.parametrize("shape", ["dag", "mixed", "fan", "slack", "wide", "chain"])
@pytest.mark.parametrize("float_days", [0, 1, 3, 20])
def test_interval_bound_produces_the_same_floats_as_the_delay_search(
    monkeypatch, shape, float_days
):
    fixture = time_network(80, shape, seed=17, float_days=float_days)
    with_bound = _time_floats(fixture)
    monkeypatch.setattr(
        time_schedule_module, "_float_limit_interval_bound", lambda *a, **k: None
    )
    with_search = _time_floats(fixture)
    assert canonical_hash(time_schedule_payload(with_bound)) == canonical_hash(
        time_schedule_payload(with_search)
    )
    assert with_bound == with_search


def test_interval_bound_is_used_for_the_hour_based_fixture(monkeypatch):
    fixture = time_network(40, "dag", seed=5)
    calls = {"bound": 0, "search": 0}
    real_bound = time_schedule_module._float_limit_interval_bound
    real_search = time_schedule_module._free_float_limit

    def counting_bound(*args, **kwargs):
        value = real_bound(*args, **kwargs)
        if value is not None:
            calls["bound"] += 1
        return value

    def counting_search(predicate):
        calls["search"] += 1
        return real_search(predicate)

    monkeypatch.setattr(time_schedule_module, "_float_limit_interval_bound", counting_bound)
    monkeypatch.setattr(time_schedule_module, "_free_float_limit", counting_search)
    _time_floats(fixture)
    assert calls["bound"] > 0
    assert calls["search"] == 0


def test_interval_bound_matches_the_search_for_signed_lags_and_all_types(monkeypatch):
    from construction_pm.scheduling.relationships import RelationshipType
    from construction_pm.scheduling.time_duration import LagQuantity
    from construction_pm.scheduling.time_forward_pass import TimeRelationship

    base = time_network(7, "chain", seed=23, float_days=12)
    for relationship_type in RelationshipType:
        for lag_hours in (-24, -8, 0, 8, 16, 40):
            relationships = tuple(
                TimeRelationship(
                    rel.predecessor_id,
                    rel.successor_id,
                    relationship_type,
                    LagQuantity.working_hours(Decimal(lag_hours)),
                )
                for rel in base.relationships
            )
            fixture = type(base)(
                activities=base.activities,
                relationships=relationships,
                registry=base.registry,
                project_start=base.project_start,
                project_finish=base.project_finish,
                size=base.size,
                shape=base.shape,
                seed=base.seed,
            )
            try:
                with_bound = _time_floats(fixture)
            except ValueError:
                # An infeasible combination is not a float-calculation input.
                continue
            monkeypatch.setattr(
                time_schedule_module, "_float_limit_interval_bound", lambda *a, **k: None
            )
            with_search = _time_floats(fixture)
            monkeypatch.undo()
            assert with_bound.floats == with_search.floats, (
                relationship_type,
                lag_hours,
            )


def test_interval_bound_falls_back_for_working_day_units():
    from construction_pm.scheduling.benchmark_fixtures import time_context
    from construction_pm.scheduling.time_duration import TimeQuantity
    from construction_pm.scheduling.time_forward_pass import (
        TimeActivity,
        TimeRelationship,
        TimeScheduledActivity,
    )

    fixture = time_network(4, "chain", seed=3)
    activity = TimeActivity("A", TimeQuantity.working_days(3), time_context())
    resolver = time_schedule_module._resolver(activity, fixture.registry)
    successor = TimeScheduledActivity(
        "B",
        datetime(2026, 1, 8, 8, tzinfo=timezone.utc),
        datetime(2026, 1, 12, 17, tzinfo=timezone.utc),
        TimeQuantity.working_days(3),
    )
    relationship = TimeRelationship(
        "A",
        "B",
        RelationshipType.FS,
        LagQuantity.working_hours(Decimal("8")),
    )
    bound = time_schedule_module._float_limit_interval_bound(
        relationship,
        activity=activity,
        base_start=datetime(2026, 1, 5, 8, tzinfo=timezone.utc),
        base_finish=datetime(2026, 1, 7, 17, tzinfo=timezone.utc),
        successor=successor,
        resolver=resolver,
        lag_resolver=resolver,
    )
    assert bound is None

