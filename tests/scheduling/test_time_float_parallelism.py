"""P0-H: exact equality of the parallel and sequential time-float paths."""

from __future__ import annotations

from datetime import datetime, time, timezone
from decimal import Decimal

import pytest

from construction_pm.scheduling.benchmark_fixtures import time_network
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
    SchedulingCalendarContext,
)
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_calendar import (
    TimeAwareWorkingTimeResolver,
    WorkingTimeCalendar,
)
from construction_pm.scheduling.time_duration import LagQuantity, TimeQuantity
from construction_pm.scheduling.time_forward_pass import TimeActivity, TimeRelationship
from construction_pm.scheduling.time_schedule import (
    _chunk_activity_ids,
    calculate_time_floats,
    time_forward_pass,
    time_backward_pass,
    time_schedule,
)


def _registry() -> CalendarResolverRegistry:
    calendar = WorkingTimeCalendar(
        daily_intervals={
            day: ((time(8), time(12)), (time(13), time(17)))
            for day in range(5)
        }
    )
    return CalendarResolverRegistry(
        time_resolvers={"site@1": TimeAwareWorkingTimeResolver(calendar)}
    )


def _context() -> SchedulingCalendarContext:
    ref = CalendarReference("site", "1", "working-time")
    return SchedulingCalendarContext(project=ref, activity=ref, relationship_lag=ref)


def _mixed_network():
    """FS/SS/FF/SF edges with positive and negative lags plus a float branch."""
    ctx = _context()
    start = datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(6), ctx),
        TimeActivity("B", TimeQuantity.working_hours(4), ctx),
        TimeActivity("C", TimeQuantity.working_hours(10), ctx),
        TimeActivity("D", TimeQuantity.working_hours(2), ctx),
        TimeActivity("E", TimeQuantity.working_hours(16), ctx),
        TimeActivity("F", TimeQuantity.working_hours(3), ctx),
    ]
    relationships = [
        TimeRelationship("A", "B", RelationshipType.FS, LagQuantity.working_hours(2)),
        TimeRelationship("A", "C", RelationshipType.SS, LagQuantity.working_hours(3)),
        TimeRelationship("B", "D", RelationshipType.FF, LagQuantity.working_hours(-1)),
        TimeRelationship("C", "D", RelationshipType.SF, LagQuantity.working_hours(1)),
        TimeRelationship("B", "E", RelationshipType.FS),
        TimeRelationship("E", "F", RelationshipType.FS, LagQuantity.working_hours(4)),
    ]
    return activities, relationships, start


def _floats(activities, relationships, start, *, workers):
    early = time_forward_pass(activities, relationships, start, _registry())
    finish = max(item.finish for item in early.values())
    late = time_backward_pass(activities, relationships, early, finish, _registry())
    return calculate_time_floats(
        activities, relationships, early, late, _registry(), workers=workers
    )


def test_parallel_floats_match_sequential_for_every_relationship_type():
    activities, relationships, start = _mixed_network()

    baseline = _floats(activities, relationships, start, workers=1)
    for workers in (2, 3):
        parallel = _floats(activities, relationships, start, workers=workers)
        assert list(parallel) == list(baseline) == sorted(item.id for item in activities)
        assert dict(parallel) == dict(baseline)
        for activity_id, value in baseline.items():
            assert parallel[activity_id] == value
            assert type(parallel[activity_id]) is type(value)


def test_parallel_floats_match_on_a_large_deterministic_network():
    fixture = time_network(200, "dag", 20261116, float_days=0)
    early = time_forward_pass(
        fixture.activities, fixture.relationships, fixture.project_start, fixture.registry
    )
    finish = fixture.project_finish or max(item.finish for item in early.values())
    late = time_backward_pass(
        fixture.activities, fixture.relationships, early, finish, fixture.registry
    )

    sequential = calculate_time_floats(
        fixture.activities,
        fixture.relationships,
        early,
        late,
        fixture.registry,
        workers=1,
    )
    parallel = calculate_time_floats(
        fixture.activities,
        fixture.relationships,
        early,
        late,
        fixture.registry,
        workers=3,
    )

    assert list(parallel) == list(sequential)
    assert dict(parallel) == dict(sequential)


def test_time_schedule_is_identical_for_one_and_two_float_workers():
    fixture = time_network(120, "dag", 20261116, float_days=3)
    sequential = time_schedule(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.project_finish,
        fixture.registry,
        float_workers=1,
    )
    parallel = time_schedule(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.project_finish,
        fixture.registry,
        float_workers=2,
    )

    assert parallel.project_finish == sequential.project_finish
    assert dict(parallel.activities) == dict(sequential.activities)
    assert dict(parallel.early_activities) == dict(sequential.early_activities)
    assert dict(parallel.late_activities) == dict(sequential.late_activities)
    assert dict(parallel.floats) == dict(sequential.floats)


def test_chunking_is_deterministic_and_covers_every_id_once():
    ids = [f"A{index:03d}" for index in range(11)]
    chunks = _chunk_activity_ids(ids, 3)
    assert [len(chunk) for chunk in chunks] == [4, 4, 3]
    assert [item for chunk in chunks for item in chunk] == ids
    assert _chunk_activity_ids(ids, 1) == [ids]
    assert _chunk_activity_ids([], 4) == [[]]


def test_invalid_float_worker_counts_are_rejected():
    activities, relationships, start = _mixed_network()
    for workers in (0, -1, True, "2"):
        with pytest.raises(ValueError):
            _floats(activities, relationships, start, workers=workers)


def test_float_values_keep_decimal_precision_across_paths():
    fixture = time_network(40, "dag", 20261116, float_days=0)
    early = time_forward_pass(
        fixture.activities, fixture.relationships, fixture.project_start, fixture.registry
    )
    finish = fixture.project_finish or max(item.finish for item in early.values())
    late = time_backward_pass(
        fixture.activities, fixture.relationships, early, finish, fixture.registry
    )
    sequential = calculate_time_floats(
        fixture.activities, fixture.relationships, early, late, fixture.registry, workers=1
    )
    parallel = calculate_time_floats(
        fixture.activities, fixture.relationships, early, late, fixture.registry, workers=4
    )
    for activity_id, value in sequential.items():
        assert isinstance(parallel[activity_id].total_float_value, Decimal)
        assert parallel[activity_id].total_float_value == value.total_float_value
        assert parallel[activity_id].free_float_value == value.free_float_value
