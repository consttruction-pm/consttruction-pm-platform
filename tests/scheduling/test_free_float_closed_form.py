"""Differential proof for the O(1) date-based Free Float boundary (P0-J).

The pre-P0-J implementation searched the delay axis with a monotone probe
(``_max_holding_delay``).  The closed form derives the same boundary from a
single calendar subtraction.  These tests compare the two on randomized
calendars, relationship types, signed lags and date windows, and compare the
complete schedule result with the probe path restored.
"""

from __future__ import annotations

import importlib
import random
from datetime import date, timedelta

import pytest

from construction_pm.scheduling.benchmark_fixtures import (
    SHAPES,
    date_network,
    date_resolver,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.forward_pass import ScheduledActivity
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.schedule import (
    _MAX_FLOAT_SEARCH,
    _holding_delay_boundary,
    _max_holding_delay,
    _relationship_holds,
    schedule,
)

schedule_module = importlib.import_module("construction_pm.scheduling.schedule")

TYPES = tuple(RelationshipType)


def _resolver(seed: int) -> WorkingTimeResolver:
    rng = random.Random(seed)
    holidays = frozenset(
        date(2026, 1, 1) + timedelta(days=rng.randrange(0, 400)) for _ in range(12)
    )
    return WorkingTimeResolver(WorkingCalendar(holidays=holidays))


def _probe_boundary(
    rel: Relationship,
    *,
    early: ScheduledActivity,
    duration: int,
    successor: ScheduledActivity,
    resolver: WorkingTimeResolver,
    lag_resolver: WorkingTimeResolver | None,
) -> int:
    def holds(delay: int) -> bool:
        candidate_start = resolver.add_working_duration(early.start, delay)
        candidate = ScheduledActivity(
            activity_id=early.activity_id,
            start=candidate_start,
            finish=resolver.add_working_duration(candidate_start, duration),
            duration=duration,
        )
        return _relationship_holds(rel, candidate, successor, resolver, lag_resolver)

    return _max_holding_delay(holds)


@pytest.mark.parametrize("seed", range(12))
def test_closed_form_matches_probe_for_every_type_and_lag(seed):
    resolver = _resolver(seed)
    rng = random.Random(seed * 31 + 7)
    for _ in range(300):
        start = date(2026, 1, 1) + timedelta(days=rng.randrange(0, 250))
        start = resolver.normalize_start(start)
        duration = rng.randrange(1, 12)
        finish = resolver.add_working_duration(start, duration)
        successor_start = resolver.normalize_start(
            finish + timedelta(days=rng.randrange(-20, 60))
        )
        successor_finish = resolver.add_working_duration(
            successor_start, rng.randrange(1, 12)
        )
        early = ScheduledActivity("A", start, finish, duration)
        successor = ScheduledActivity("B", successor_start, successor_finish, 1)
        rel = Relationship("A", "B", TYPES[rng.randrange(len(TYPES))], lag=rng.randrange(-4, 6))

        probe = _probe_boundary(
            rel,
            early=early,
            duration=duration,
            successor=successor,
            resolver=resolver,
            lag_resolver=None,
        )
        closed = _holding_delay_boundary(
            rel,
            base_start=start,
            base_finish=finish,
            successor=successor,
            resolver=resolver,
            lag_resolver=None,
        )
        assert closed is not None
        assert probe == closed, (rel, start, finish, successor_start, successor_finish)


def test_closed_form_caps_exactly_like_the_probe_search():
    resolver = date_resolver()
    start = resolver.normalize_start(date(2026, 1, 1))
    finish = resolver.add_working_duration(start, 2)
    # A successor decades away keeps every bounded delay valid.
    far = resolver.add_working_duration(finish, _MAX_FLOAT_SEARCH + 500)
    rel = Relationship("A", "B", RelationshipType.FS, lag=0)
    early = ScheduledActivity("A", start, finish, 2)
    successor = ScheduledActivity("B", far, far, 1)

    probe = _probe_boundary(
        rel, early=early, duration=2, successor=successor, resolver=resolver, lag_resolver=None
    )
    closed = _holding_delay_boundary(
        rel,
        base_start=start,
        base_finish=finish,
        successor=successor,
        resolver=resolver,
        lag_resolver=None,
    )
    assert probe == _MAX_FLOAT_SEARCH
    # ``_max_holding_delay`` reports the 10,000 sentinel when every bounded
    # delay holds; callers publish ``min(boundary, 9_999)``.  The closed form
    # publishes that capped value directly.
    assert min(probe, _MAX_FLOAT_SEARCH - 1) == closed


def test_different_lag_calendar_keeps_the_probe_path():
    resolver = _resolver(3)
    other = _resolver(4)
    start = resolver.normalize_start(date(2026, 2, 2))
    finish = resolver.add_working_duration(start, 3)
    rel = Relationship("A", "B", RelationshipType.FS, lag=1)
    early = ScheduledActivity("A", start, finish, 3)
    successor = ScheduledActivity("B", finish, finish, 1)
    assert (
        _holding_delay_boundary(
            rel,
            base_start=start,
            base_finish=finish,
            successor=successor,
            resolver=resolver,
            lag_resolver=other,
        )
        is None
    )


@pytest.mark.parametrize("shape", SHAPES)
@pytest.mark.parametrize("size", (1, 2, 40, 250))
def test_schedule_result_is_identical_with_and_without_the_closed_form(shape, size, monkeypatch):
    fixture = date_network(size, shape, seed=11)
    resolver = date_resolver()

    with_closed_form = schedule(
        fixture.activities, fixture.relationships, fixture.project_start, resolver
    )
    monkeypatch.setattr(schedule_module, "_holding_delay_boundary", lambda *a, **k: None)
    with_probes = schedule(
        fixture.activities, fixture.relationships, fixture.project_start, resolver
    )
    monkeypatch.undo()
    assert with_closed_form == with_probes


def test_closed_form_eliminates_probe_searches(monkeypatch):
    fixture = date_network(200, "dag", seed=5)
    calls = {"count": 0}
    original = schedule_module._max_holding_delay

    def counting(predicate):
        calls["count"] += 1
        return original(predicate)

    monkeypatch.setattr(schedule_module, "_max_holding_delay", counting)
    schedule(fixture.activities, fixture.relationships, fixture.project_start, date_resolver())
    assert calls["count"] == 0
