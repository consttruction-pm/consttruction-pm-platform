"""Deterministic, seeded fixtures and canonical output hashing for the P0 baseline.

The P0 scheduling-core work must prove that every optimisation produces exactly
the same canonical result as the unchanged reference engine for identical
immutable inputs.  That requires fixtures that are reproducible on every
machine and a canonical byte-level digest of the engine output.

Nothing in this module changes scheduling behaviour.  It only builds inputs and
serialises outputs, so it is safe to import from the benchmark CLI, from tests
and, later, from the worker supervision harness.

Design rules
------------
* Fixtures are pure functions of ``(size, shape, seed)``; no wall-clock, no
  hash randomisation and no version-dependent pseudo random generator is used.
  The small LCG below is stable across Python versions and platforms.
* Every network is a DAG by construction because an edge only ever points from
  a lower index to a higher index.  Cyclic inputs are covered by dedicated
  tests, not by these scale fixtures.
* Durations, lags and role patterns are derived from the index, so raising the
  size extends the same network instead of reshuffling it.
"""

from __future__ import annotations

import hashlib
import json
import platform
import resource
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, time as day_time, timedelta, timezone
from decimal import Decimal
from typing import Callable, Iterable, Mapping, Sequence

from .activity import Activity
from .calendar import WorkingCalendar, WorkingTimeResolver
from .calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
    SchedulingCalendarContext,
)
from .relationships import Relationship, RelationshipType
from .resource_leveling import (
    BackwardLevelingActivity,
    LevelingActivity,
    LevelingShift,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingOptions,
    propose_forward_leveling_within_float,
)
from .leveling_boundary import SchedulerLevelingInput
from .leveling_scheduler import schedule_with_resource_leveling
from .schedule import ScheduleResult, schedule
from .schedule_options import ScheduleOptions
from .time_calendar import TimeAwareWorkingTimeResolver, WorkingTimeCalendar
from .time_duration import LagQuantity, TimeQuantity
from .time_forward_pass import TimeActivity, TimeRelationship, time_forward_pass
from .time_schedule import TimeScheduleResult, time_schedule

PROJECT_START = date(2026, 1, 5)  # Monday
TIME_PROJECT_START = datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)

SHAPES = ("chain", "wide", "dag", "fan", "mixed", "slack")

_RELATIONSHIP_CYCLE = (
    RelationshipType.FS,
    RelationshipType.SS,
    RelationshipType.FF,
    RelationshipType.SF,
)
_LAG_CYCLE = (0, 0, 1, -1, 2)

MAX_DATE_LINEARITY_RELATIONSHIP_EDGE = 2


class _StableLcg:
    """Tiny deterministic generator that is identical across Python versions."""

    def __init__(self, seed: int) -> None:
        self._state = seed & 0x7FFFFFFF

    def next(self) -> int:
        self._state = (1103515245 * self._state + 12345) & 0x7FFFFFFF
        return self._state

    def below(self, bound: int) -> int:
        if bound <= 0:
            raise ValueError("bound must be positive")
        # Use the high bits: the low bits of this generator repeat quickly for
        # small seeds, which would make neighbouring seeds produce the same
        # network.
        return (self.next() >> 8) % bound


def activity_id(index: int) -> str:
    return f"ACT-{index:07d}"


def resource_id(index: int) -> str:
    return f"RES-{index:03d}"


# ---------------------------------------------------------------------------
# Networks
# ---------------------------------------------------------------------------


def _edges(size: int, shape: str, seed: int) -> list[tuple[int, int, int]]:
    """Return ``(predecessor_index, successor_index, edge_index)`` triples."""

    if shape not in SHAPES:
        raise ValueError(f"unsupported fixture shape: {shape!r}")
    if size < 0:
        raise ValueError("size must be non-negative")

    if shape == "wide":
        return []
    if shape == "chain":
        return [(index - 1, index, index - 1) for index in range(1, size)]
    if shape == "fan":
        if size < 3:
            return [(index - 1, index, index - 1) for index in range(1, size)]
        edges = [(0, index, index - 1) for index in range(1, size - 1)]
        edges.extend((index, size - 1, size - 2 + index) for index in range(1, size - 1))
        return edges
    if shape == "slack":
        # A spine of roughly half the network plus short free-standing
        # activities that all feed the last activity.  The short activities
        # therefore carry a large Free Float, which is the shape that makes the
        # Time-Aware Free Float search visible in a benchmark.
        if size < 4:
            return [(index - 1, index, index - 1) for index in range(1, size)]
        spine = max(1, size // 2)
        edges = [(index - 1, index, index - 1) for index in range(1, spine)]
        last = size - 1
        edges.append((spine - 1, last, len(edges)))
        edges.extend((index, last, len(edges) + index) for index in range(spine, last))
        return edges

    rng = _StableLcg(seed)
    seen: set[tuple[int, int]] = set()
    edges: list[tuple[int, int, int]] = []
    edge_index = 0
    for index in range(1, size):
        # Always keep one spine edge so every node is reachable and the
        # network stays connected.
        candidates = [index - 1]
        span = 2 + (rng.below(6) if shape == "mixed" else rng.below(4))
        extra = 1 + rng.below(MAX_DATE_LINEARITY_RELATIONSHIP_EDGE)
        for _ in range(extra):
            candidate = index - 1 - rng.below(span)
            if candidate >= 0:
                candidates.append(candidate)
        for predecessor in candidates:
            if predecessor < 0 or predecessor == index:
                continue
            key = (predecessor, index)
            if key in seen:
                continue
            seen.add(key)
            edges.append((predecessor, index, edge_index))
            edge_index += 1
    return edges


@dataclass(frozen=True)
class DateFixture:
    activities: tuple[Activity, ...]
    relationships: tuple[Relationship, ...]
    project_start: date
    size: int
    shape: str
    seed: int

    @property
    def counts(self) -> dict[str, int]:
        return {"activities": len(self.activities), "relationships": len(self.relationships)}


def date_network(size: int, shape: str = "dag", seed: int = 20261116) -> DateFixture:
    """Build a deterministic working-day CPM network."""

    activities = tuple(
        Activity(activity_id(index), duration=(index % 5) + 1)
        for index in range(size)
    )
    relationships: list[Relationship] = []
    for predecessor, successor, edge_index in _edges(size, shape, seed):
        if shape == "mixed":
            relationship_type = _RELATIONSHIP_CYCLE[edge_index % len(_RELATIONSHIP_CYCLE)]
            lag = _LAG_CYCLE[edge_index % len(_LAG_CYCLE)]
        else:
            relationship_type = RelationshipType.FS
            lag = 0
        relationships.append(
            Relationship(
                activity_id(predecessor),
                activity_id(successor),
                relationship_type,
                lag=lag,
            )
        )
    return DateFixture(activities, tuple(relationships), PROJECT_START, size, shape, seed)


def date_resolver() -> WorkingTimeResolver:
    # Fixed holidays keep the fixture stable across years; the network start is
    # in 2026 so these dates are always inside the scheduled horizon.
    return WorkingTimeResolver(
        WorkingCalendar(
            holidays=frozenset(
                {
                    date(2026, 1, 6),
                    date(2026, 2, 17),
                    date(2026, 3, 20),
                    date(2026, 4, 3),
                }
            )
        )
    )


@dataclass(frozen=True)
class TimeFixture:
    activities: tuple[TimeActivity, ...]
    relationships: tuple[TimeRelationship, ...]
    registry: CalendarResolverRegistry
    project_start: datetime
    project_finish: datetime | None
    size: int
    shape: str
    seed: int

    @property
    def counts(self) -> dict[str, int]:
        return {"activities": len(self.activities), "relationships": len(self.relationships)}


def time_calendar() -> WorkingTimeCalendar:
    interval = ((day_time(8), day_time(12)), (day_time(13), day_time(17)))
    return WorkingTimeCalendar(
        holidays=frozenset({date(2026, 1, 6), date(2026, 2, 17), date(2026, 3, 20)}),
        daily_intervals={weekday: interval for weekday in range(5)},
    )


def time_registry() -> CalendarResolverRegistry:
    return CalendarResolverRegistry(
        time_resolvers={"site@1": TimeAwareWorkingTimeResolver(time_calendar())}
    )


def time_context() -> SchedulingCalendarContext:
    reference = CalendarReference("site", "1", "working-time")
    return SchedulingCalendarContext(
        project=reference,
        activity=reference,
        relationship_lag=reference,
    )


def time_network(
    size: int,
    shape: str = "dag",
    seed: int = 20261116,
    float_days: int = 0,
) -> TimeFixture:
    """Build a deterministic time-aware network.

    ``float_days`` is applied to the project finish so the Time-Aware Free
    Float probe has a bounded, known search range instead of the 9999 sentinel.
    The finish is derived from a real forward pass, never estimated, and the
    extra pass is reported separately by the benchmark CLI.
    """

    context = time_context()
    activities = tuple(
        TimeActivity(
            activity_id(index),
            TimeQuantity.working_hours(((index % 5) + 1) * 8),
            context,
        )
        for index in range(size)
    )
    relationships: list[TimeRelationship] = []
    for predecessor, successor, edge_index in _edges(size, shape, seed):
        if shape == "mixed":
            relationship_type = _RELATIONSHIP_CYCLE[edge_index % len(_RELATIONSHIP_CYCLE)]
            lag_value = _LAG_CYCLE[edge_index % len(_LAG_CYCLE)]
        else:
            relationship_type = RelationshipType.FS
            lag_value = 0
        relationships.append(
            TimeRelationship(
                activity_id(predecessor),
                activity_id(successor),
                relationship_type,
                LagQuantity.working_hours(Decimal(lag_value) * Decimal("8")),
            )
        )
    registry = time_registry()
    project_finish: datetime | None = None
    if activities and float_days >= 0:
        early = time_forward_pass(
            activities,
            relationships,
            TIME_PROJECT_START,
            registry,
        )
        latest = max(item.finish for item in early.values())
        resolver = TimeAwareWorkingTimeResolver(time_calendar())
        project_finish = resolver.add_working_hours(
            latest, Decimal(float_days) * Decimal("8")
        )
    return TimeFixture(
        activities,
        tuple(relationships),
        registry,
        TIME_PROJECT_START,
        project_finish,
        size,
        shape,
        seed,
    )


@dataclass(frozen=True)
class LevelingFixture:
    activities: tuple[LevelingActivity, ...]
    capacities: tuple[ResourceCapacity, ...]
    resolver: WorkingTimeResolver
    size: int
    seed: int

    @property
    def counts(self) -> dict[str, int]:
        return {
            "activities": len(self.activities),
            "capacities": len(self.capacities),
            "resources": len({capacity.resource_id for capacity in self.capacities}),
        }


def leveling_case(
    size: int,
    seed: int = 20261116,
    *,
    resources: int = 2,
    activities_per_wave: int = 8,
    duration_days: int = 2,
    demand_units: Decimal = Decimal("4"),
    capacity_units: Decimal = Decimal("8"),
    total_float: int = 10,
) -> LevelingFixture:
    """Build a deterministic over-allocated leveling case.

    Activities are grouped into waves that share a start day, and every wave
    over-allocates its resource, so the leveling pass has real work to do.  The
    capacity horizon extends past the longest possible shift so a shift is
    never rejected because capacity facts were missing.
    """

    if size < 0:
        raise ValueError("size must be non-negative")
    if resources < 1 or activities_per_wave < 1 or duration_days < 1:
        raise ValueError("resources, activities_per_wave and duration_days must be positive")
    rng = _StableLcg(seed)
    resolver = date_resolver()
    horizon_days = ((size // activities_per_wave) + 2) * duration_days + total_float + 5
    days: list[date] = []
    cursor = resolver.normalize_start(PROJECT_START)
    for _ in range(horizon_days):
        days.append(cursor)
        cursor = resolver.next_working_day(cursor + timedelta(days=1))

    activities: list[LevelingActivity] = []
    for index in range(size):
        wave = index // activities_per_wave
        start_offset = wave * duration_days
        start = days[start_offset]
        finish = resolver.add_working_duration(start, duration_days)
        resource = resource_id(index % resources)
        demand_periods: list[date] = []
        period = start
        for _ in range(duration_days):
            demand_periods.append(period)
            period = resolver.next_working_day(period + timedelta(days=1))
        demands = tuple(
            ResourceDemand(resource, period, demand_units, activity_id(index))
            for period in demand_periods
        )
        activities.append(
            LevelingActivity(
                activity_id(index),
                start,
                finish,
                total_float,
                demands,
                activity_priority=(index % 4),
            )
        )
        # Keep the generator exercised so future patterns stay deterministic
        # without changing today's layout.
        rng.next()

    capacities = tuple(
        ResourceCapacity(resource_id(index % resources), day, capacity_units)
        for day in days
        for index in range(resources)
    )
    return LevelingFixture(tuple(activities), capacities, resolver, size, seed)


# ---------------------------------------------------------------------------
# Full leveling orchestration (forward proposal + backward acceptance + CPM)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LevelingOrchestrationFixture:
    activities: tuple[Activity, ...]
    relationships: tuple[Relationship, ...]
    project_start: date
    project_finish: date
    resolver: WorkingTimeResolver
    leveling_input: object
    options: object
    size: int
    shape: str
    seed: int

    @property
    def counts(self) -> dict[str, int]:
        return {
            "activities": len(self.activities),
            "relationships": len(self.relationships),
            "forward_activities": len(self.leveling_input.forward_activities),
            "backward_activities": len(self.leveling_input.backward_activities),
            "capacities": len(self.leveling_input.capacities),
        }


def leveling_orchestration_case(
    size: int,
    seed: int = 20261116,
    *,
    duration_days: int = 2,
    demand_units: Decimal = Decimal("4"),
    capacity_units: Decimal = Decimal("8"),
    float_slack_working_days: int | None = None,
) -> LevelingOrchestrationFixture:
    """Build a leveling case that the full orchestrator can actually resolve.

    The activities are independent (no relationships) and all start on the
    project start day, each holding ``demand_units`` for ``duration_days``
    working days while daily capacity allows only two of them at once.  That
    leaves a large, unambiguous forward backlog and no relationship that could
    make a shift infeasible.  The project finish is placed
    ``float_slack_working_days`` working days after the early finish so every
    activity has the float the forward pass needs; once forward leveling has
    spread the backlog the late window has no overload left, so this fixture
    measures the forward path and the closing pass, not backward acceptance.

    The fixture is deliberately independent-of-network-shape: P0-E is about the
    number of CPM passes the orchestrator performs, not about a particular
    relationship topology, which the date and time benchmarks already cover.
    """

    if size < 2:
        raise ValueError("size must be at least 2")
    if duration_days < 1:
        raise ValueError("duration_days must be positive")
    if float_slack_working_days is None:
        # Two working days of float per activity is enough to serialize the
        # whole starting backlog, plus a margin for holidays.
        float_slack_working_days = max(20, 2 * size + 10)
    if float_slack_working_days < 1:
        raise ValueError("float_slack_working_days must be positive")

    rng = _StableLcg(seed)
    resolver = date_resolver()
    project_start = resolver.normalize_start(PROJECT_START)
    early_finish = resolver.add_working_duration(project_start, duration_days)
    project_finish = resolver.add_working_duration(
        early_finish, float_slack_working_days + 1
    )

    activities = tuple(Activity(activity_id(index), duration=duration_days) for index in range(size))
    initial = schedule(activities, (), project_start, resolver, project_finish=project_finish)
    early = initial.early_activities or initial.activities
    late = initial.late_activities or initial.activities
    floats = initial.floats
    resource = resource_id(0)

    forward: list[LevelingActivity] = []
    backward: list[BackwardLevelingActivity] = []
    period_days: list[date] = []
    cursor = project_start
    for _ in range(duration_days):
        period_days.append(cursor)
        cursor = resolver.next_working_day(cursor)

    for index, activity in enumerate(activities):
        early_activity = early[activity.id]
        late_activity = late[activity.id]
        float_activity = floats[activity.id]
        demands = tuple(
            ResourceDemand(resource, period, demand_units, activity.id)
            for period in period_days
        )
        priority = index % 4
        forward.append(
            LevelingActivity(
                activity.id,
                early_activity.start,
                early_activity.finish,
                float_activity.total_float,
                demands,
                activity_priority=priority,
            )
        )
        backward.append(
            BackwardLevelingActivity(
                activity.id,
                early_activity.start,
                early_activity.finish,
                late_activity.start,
                late_activity.finish,
                demands,
                activity_priority=priority,
            )
        )
        # Keep the generator exercised so future patterns stay deterministic
        # without changing today's layout.
        rng.next()

    capacities: list[ResourceCapacity] = []
    cursor = project_start
    horizon_end = resolver.add_working_duration(
        project_finish, float_slack_working_days + 1
    )
    while cursor <= horizon_end:
        capacities.append(ResourceCapacity(resource, cursor, capacity_units))
        cursor = resolver.next_working_day(cursor)

    leveling_input = SchedulerLevelingInput(
        forward_activities=tuple(forward),
        backward_activities=tuple(backward),
        capacities=tuple(capacities),
        options=ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=False,
            level_all_resources=True,
            level_within_float=True,
        ),
    )
    options = ScheduleOptions(
        level_all_resources=True,
        level_within_float=True,
        preserve_scheduled_early_and_late_dates=False,
    )
    return LevelingOrchestrationFixture(
        activities=activities,
        relationships=(),
        project_start=project_start,
        project_finish=project_finish,
        resolver=resolver,
        leveling_input=leveling_input,
        options=options,
        size=size,
        shape="flat",
        seed=seed,
    )


# ---------------------------------------------------------------------------
# Canonical serialisation
# ---------------------------------------------------------------------------


def _iso(value: date | datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _decimal(value: Decimal | int | None) -> str | None:
    return None if value is None else str(value)


def _sorted_items(mapping: Mapping[str, object]) -> Iterable[tuple[str, object]]:
    return ((key, mapping[key]) for key in sorted(mapping))


def date_schedule_payload(result: ScheduleResult) -> dict[str, object]:
    activities = {
        activity_id: {
            "start": _iso(item.start),
            "finish": _iso(item.finish),
            "duration": item.duration,
            "remaining_start": _iso(item.remaining_start),
            "remaining_finish": _iso(item.remaining_finish),
            "percent_complete": item.percent_complete,
            "status": item.status.value if item.status is not None else None,
        }
        for activity_id, item in _sorted_items(result.early_activities or {})
    }
    late = {
        activity_id: {
            "start": _iso(item.start),
            "finish": _iso(item.finish),
            "duration": item.duration,
        }
        for activity_id, item in _sorted_items(result.late_activities or {})
    }
    floats = {
        activity_id: {
            "early_start": _iso(item.early_start),
            "early_finish": _iso(item.early_finish),
            "late_start": _iso(item.late_start),
            "late_finish": _iso(item.late_finish),
            "total_float": item.total_float,
            "free_float": item.free_float,
            "critical": item.critical,
            "float_path": item.float_path,
            "float_path_order": item.float_path_order,
        }
        for activity_id, item in _sorted_items(result.floats)
    }
    diagnostics = [
        {
            "code": item.code.value,
            "severity": item.severity.value,
            "message": item.message,
            "activity_id": item.activity_id,
            "predecessor_id": item.predecessor_id,
            "successor_id": item.successor_id,
        }
        for item in result.diagnostics
    ]
    return {
        "project_finish": _iso(result.project_finish),
        "mode": result.mode.value,
        "activities": activities,
        "late": late,
        "floats": floats,
        "diagnostics": diagnostics,
    }


def time_schedule_payload(result: TimeScheduleResult) -> dict[str, object]:
    def activity(item) -> dict[str, object]:
        return {
            "start": _iso(item.start),
            "finish": _iso(item.finish),
            "duration": str(item.duration.value),
            "unit": item.duration.unit.value,
        }

    return {
        "project_finish": _iso(result.project_finish),
        "early": {
            activity_id: activity(item)
            for activity_id, item in _sorted_items(result.early_activities)
        },
        "late": {
            activity_id: activity(item)
            for activity_id, item in _sorted_items(result.late_activities)
        },
        "floats": {
            activity_id: {
                "early_start": _iso(item.early_start),
                "early_finish": _iso(item.early_finish),
                "late_start": _iso(item.late_start),
                "late_finish": _iso(item.late_finish),
                "total_float_hours": _decimal(item.total_float_hours),
                "free_float_hours": _decimal(item.free_float_hours),
                "total_float_value": str(item.total_float_value),
                "free_float_value": str(item.free_float_value),
                "float_unit": item.float_unit.value,
                "critical": item.critical,
            }
            for activity_id, item in _sorted_items(result.floats)
        },
    }


def leveling_payload(shifts: Sequence[LevelingShift]) -> dict[str, object]:
    return {
        "shifts": [
            {
                "activity_id": item.activity_id,
                "shift_working_days": item.shift_working_days,
                "new_start": _iso(item.new_start),
                "new_finish": _iso(item.new_finish),
                "consumed_float": item.consumed_float,
                "remaining_float": item.remaining_float,
            }
            for item in shifts
        ]
    }


def leveling_orchestration_payload(
    result: ScheduleResult,
    forward: Sequence[LevelingShift],
    backward: Sequence[object],
) -> dict[str, object]:
    """Canonical digest input for the full leveling orchestration.

    The payload covers the published CPM result and both accepted shift lists,
    so a reuse of an identical earlier CPM pass cannot hide a changed output.
    """
    return {
        "schedule": date_schedule_payload(result),
        "forward_shifts": [
            {
                "activity_id": item.activity_id,
                "shift_working_days": item.shift_working_days,
                "new_start": _iso(item.new_start),
                "new_finish": _iso(item.new_finish),
                "consumed_float": item.consumed_float,
                "remaining_float": item.remaining_float,
            }
            for item in forward
        ],
        "backward_shifts": [
            {
                "activity_id": item.activity_id,
                "shift_working_days": item.shift_working_days,
                "new_start": _iso(item.new_start),
                "new_finish": _iso(item.new_finish),
                "advanced_days": item.advanced_days,
            }
            for item in backward
        ],
    }


def canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_hash(payload: object) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TimingSummary:
    count: int
    minimum_ms: float
    median_ms: float
    p95_ms: float
    maximum_ms: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "count": self.count,
            "min_ms": round(self.minimum_ms, 3),
            "median_ms": round(self.median_ms, 3),
            "p95_ms": round(self.p95_ms, 3),
            "max_ms": round(self.maximum_ms, 3),
        }


def summarize_ms(samples: Sequence[float]) -> TimingSummary:
    if not samples:
        raise ValueError("at least one sample is required")
    ordered = sorted(samples)
    index = min(len(ordered) - 1, max(0, int(round(0.95 * (len(ordered) - 1)))))
    return TimingSummary(
        count=len(ordered),
        minimum_ms=ordered[0],
        median_ms=statistics.median(ordered),
        p95_ms=ordered[index],
        maximum_ms=ordered[-1],
    )


def peak_rss_kb() -> int:
    """Process peak RSS in kibibytes (Linux ``ru_maxrss`` unit)."""

    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def measure(
    operation: Callable[[], object],
    *,
    repeat: int = 1,
    warmup: int = 0,
) -> dict[str, object]:
    """Run ``operation`` and return real wall/CPU samples and peak RSS.

    Peak RSS is a process-level high-water mark, so callers should run one
    measurement per process when the figure must be attributable to one shape.
    """

    if repeat < 1:
        raise ValueError("repeat must be at least 1")
    for _ in range(warmup):
        operation()
    wall: list[float] = []
    cpu: list[float] = []
    result: object = None
    for _ in range(repeat):
        wall_start = time.perf_counter()
        cpu_start = time.process_time()
        result = operation()
        wall.append((time.perf_counter() - wall_start) * 1000.0)
        cpu.append((time.process_time() - cpu_start) * 1000.0)
    return {
        "wall": summarize_ms(wall).as_dict(),
        "cpu": summarize_ms(cpu).as_dict(),
        "peak_rss_kb": peak_rss_kb(),
        "result": result,
    }


# ---------------------------------------------------------------------------
# Mode runners used by the CLI and by later differential tests
# ---------------------------------------------------------------------------


def run_date_schedule(fixture: DateFixture) -> ScheduleResult:
    return schedule(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        date_resolver(),
    )


def run_time_schedule(
    fixture: TimeFixture, *, float_workers: int = 1
) -> TimeScheduleResult:
    return time_schedule(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.project_finish,
        fixture.registry,
        float_workers=float_workers,
    )


def run_leveling(fixture: LevelingFixture) -> tuple[LevelingShift, ...]:
    return propose_forward_leveling_within_float(
        fixture.activities,
        fixture.capacities,
        resolver=fixture.resolver,
    )


def run_leveling_orchestration(
    fixture: LevelingOrchestrationFixture,
):
    return schedule_with_resource_leveling(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.resolver,
        fixture.leveling_input,
        project_finish=fixture.project_finish,
        options=fixture.options,
    )


def environment_fingerprint(git_sha: str | None = None) -> dict[str, object]:
    try:
        affinity = len(__import__("os").sched_getaffinity(0))
    except (AttributeError, OSError):  # pragma: no cover - non-Linux
        affinity = None
    memory_total_kb = None
    try:
        with open("/proc/meminfo", encoding="ascii") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    memory_total_kb = int(line.split()[1])
                    break
    except OSError:  # pragma: no cover - non-Linux
        memory_total_kb = None
    return {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": __import__("os").cpu_count(),
        "cpu_affinity_count": affinity,
        "memory_total_kb": memory_total_kb,
        "git_sha": git_sha,
    }
