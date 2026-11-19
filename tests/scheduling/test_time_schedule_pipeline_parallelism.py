"""P0-M: exact equality and fallback proof for the backward/float pipeline.

The pipeline overlaps the backward pass with the per-activity float
calculation. Every test compares it against the sequential Oracle at one,
two and four worker slots: early dates, late dates, total and free float,
critical flags, project finish and the canonical payload hash must be
identical, and every fallback must run the historical loop unchanged.
"""

from __future__ import annotations

import importlib
import threading
from datetime import date, datetime, time, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

# ``construction_pm.scheduling.time_schedule`` is also re-exported as a
# function from the package, so a plain ``import ... as ts`` would bind the
# function instead of the module. Resolve the module explicitly.
ts = importlib.import_module("construction_pm.scheduling.time_schedule")
from construction_pm.scheduling import benchmark_fixtures as fixtures
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
    SchedulingCalendarContext,
)
from construction_pm.scheduling.calendar_exception_overlay import CalendarExceptionLayers
from construction_pm.scheduling.calendar_exceptions import (
    CalendarException,
    CalendarExceptionType,
)
from construction_pm.scheduling.schedule_options import StartToStartLagCalculationType
from construction_pm.scheduling.time_calendar import (
    TimeAwareWorkingTimeResolver,
    WorkingTimeCalendar,
)
from construction_pm.scheduling.time_constraints import (
    TimeActivityConstraint,
    TimeConstraintType,
)
from construction_pm.scheduling.time_forward_pass import (
    TimeActivity,
    TimeRelationship,
)
from construction_pm.scheduling.time_schedule import (
    FloatExecutionPolicy,
    TimeScheduleOptions,
    TimeScheduleResult,
    _float_pipeline,
    _time_float_context,
    _time_float_for_activity,
    calculate_time_floats,
    time_backward_pass,
    time_schedule,
)
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import LagQuantity, TimeQuantity

UTC = timezone.utc
NETWORK_SIZE = 320  # above the pipeline threshold, so the pool really starts

SHAPES = [RelationshipType.FS, RelationshipType.SS, RelationshipType.FF, RelationshipType.SF]
LAGS = [Decimal("0"), Decimal("4"), Decimal("-1"), Decimal("2"), Decimal("8")]


def _hours(value: Decimal | int) -> TimeQuantity:
    return TimeQuantity.working_hours(value)


def _calendar(
    intervals: tuple[tuple[time, time], ...] = (
        (time(8), time(12)),
        (time(13), time(17)),
    ),
    *,
    holidays: tuple[date, ...] = (),
) -> WorkingTimeCalendar:
    return WorkingTimeCalendar(
        holidays=frozenset(holidays),
        daily_intervals={day: intervals for day in range(5)},
    )


def _reference(name: str = "site") -> CalendarReference:
    return CalendarReference(name, "1", "working-time")


def _context(
    project: CalendarReference | None = None,
    activity: CalendarReference | None = None,
    lag: CalendarReference | None = None,
) -> SchedulingCalendarContext:
    project = project or _reference()
    return SchedulingCalendarContext(
        project=project,
        activity=activity or project,
        relationship_lag=lag or project,
    )


def _network(
    size: int = NETWORK_SIZE,
    *,
    context: SchedulingCalendarContext | None = None,
    duration_cycle: tuple[int, ...] = (8, 16, 24, 40),
) -> tuple[list[TimeActivity], list[TimeRelationship]]:
    """Deterministic spine plus forward shortcuts and a few free activities."""

    context = context or _context()
    activities = [
        TimeActivity(f"a{index:05d}", _hours(duration_cycle[index % len(duration_cycle)]), context)
        for index in range(size - 6)
    ]
    relationships: list[TimeRelationship] = []
    for index in range(1, len(activities)):
        relationships.append(TimeRelationship(activities[index - 1].id, activities[index].id))
    edge = 0
    for index in range(0, len(activities) - 2):
        span = 2 + (index % 4)
        target = index + span
        if target < len(activities):
            relationships.append(
                TimeRelationship(
                    activities[index].id,
                    activities[target].id,
                    SHAPES[edge % len(SHAPES)],
                    LagQuantity(LAGS[edge % len(LAGS)], ts.DurationUnit.WORKING_HOUR),
                )
            )
            edge += 1
    # Activities with no relationship at all: they must still get floats.
    for offset in range(6):
        activities.append(
            TimeActivity(f"z{offset:05d}", _hours(duration_cycle[offset % len(duration_cycle)]), context)
        )
    return activities, relationships


def _run(
    activities: list[TimeActivity],
    relationships: list[TimeRelationship],
    registry: CalendarResolverRegistry,
    *,
    workers: int,
    policy: FloatExecutionPolicy | None = None,
    project_start: datetime = datetime(2026, 10, 12, 8, tzinfo=UTC),
    project_finish: datetime | None = None,
    constraints: tuple[TimeActivityConstraint, ...] = (),
    options: TimeScheduleOptions | None = None,
) -> TimeScheduleResult:
    return time_schedule(
        activities,
        relationships,
        project_start,
        project_finish,
        registry,
        constraints,
        options,
        float_workers=workers,
        float_policy=policy,
    )


def _fingerprint(result: TimeScheduleResult) -> dict[str, object]:
    payload = fixtures.time_schedule_payload(result)
    payload["sha256"] = fixtures.canonical_hash(payload)
    return payload


def _assert_same(sequential: TimeScheduleResult, parallel: TimeScheduleResult) -> None:
    assert _fingerprint(parallel) == _fingerprint(sequential)
    assert list(parallel.floats) == list(sequential.floats)
    assert list(parallel.early_activities) == list(sequential.early_activities)
    assert list(parallel.late_activities) == list(sequential.late_activities)
    assert parallel.project_finish == sequential.project_finish


def _pipeline_available() -> bool:
    return ts._fork_is_safe()


requires_fork = pytest.mark.skipif(
    not _pipeline_available(), reason="fork is not a safe start method here"
)


@pytest.fixture()
def single_calendar_registry() -> CalendarResolverRegistry:
    return CalendarResolverRegistry(
        time_resolvers={"site@1": TimeAwareWorkingTimeResolver(_calendar())}
    )


@pytest.fixture()
def pipeline_counter(monkeypatch):
    """Count completed pipeline runs so a test can prove the pool was used."""

    counter = {"runs": 0, "batches": 0}
    original = ts._FloatPipeline

    class CountingPipeline(original):
        def finish(self):
            result = super().finish()
            counter["runs"] += 1
            counter["batches"] += self.dispatched_batches
            return result

    monkeypatch.setattr(ts, "_FloatPipeline", CountingPipeline)
    return counter


# ---------------------------------------------------------------------------
# Equality across worker counts
# ---------------------------------------------------------------------------


@requires_fork
@pytest.mark.parametrize("workers", [2, 4])
def test_pipeline_matches_sequential_on_mixed_network(
    single_calendar_registry, pipeline_counter, workers
):
    activities, relationships = _network()
    sequential = _run(activities, relationships, single_calendar_registry, workers=1)
    parallel = _run(
        activities, relationships, single_calendar_registry, workers=workers
    )
    _assert_same(sequential, parallel)
    assert pipeline_counter["runs"] == 1
    assert pipeline_counter["batches"] == -(-len(activities) // ts._pipeline_batch_size(len(activities)))


@requires_fork
def test_pipeline_matches_sequential_across_calendars_and_exceptions():
    project_ref = _reference("project")
    site = _reference("site")
    fast = _reference("fast")
    lag = _reference("lag")
    registry = CalendarResolverRegistry(
        time_resolvers={
            "project@1": TimeAwareWorkingTimeResolver(_calendar()),
            "site@1": TimeAwareWorkingTimeResolver(
                _calendar(holidays=(date(2026, 10, 21), date(2026, 10, 28)))
            ),
            "fast@1": TimeAwareWorkingTimeResolver(
                _calendar(((time(7), time(11)), (time(11, 30), time(15)), (time(16), time(19))))
            ),
            "lag@1": TimeAwareWorkingTimeResolver(_calendar(((time(9), time(12)),))),
        },
        exception_layers={
            "site@1": CalendarExceptionLayers(
                local=(
                    CalendarException(date(2026, 10, 22), CalendarExceptionType.NONWORK),
                    CalendarException(
                        date(2026, 10, 23),
                        CalendarExceptionType.DETAILED_WORK_HOURS,
                        intervals=((time(8), time(10)),),
                    ),
                )
            )
        },
    )
    context = SchedulingCalendarContext(
        project=project_ref, activity=site, relationship_lag=lag
    )
    fast_context = SchedulingCalendarContext(
        project=project_ref, activity=fast, relationship_lag=lag
    )
    activities, relationships = _network(context=context)
    activities = [
        activity
        if index % 5
        else TimeActivity(activity.id, activity.duration, fast_context)
        for index, activity in enumerate(activities)
    ]
    sequential = _run(activities, relationships, registry, workers=1)
    for workers in (2, 4):
        _assert_same(
            sequential, _run(activities, relationships, registry, workers=workers)
        )


@requires_fork
def test_pipeline_matches_sequential_across_dst_and_time_zone():
    zone = ZoneInfo("America/New_York")
    registry = CalendarResolverRegistry(
        time_resolvers={"site@1": TimeAwareWorkingTimeResolver(_calendar())}
    )
    activities, relationships = _network()
    # DST ends in New York on 2026-11-01; the network spans several weeks.
    start = datetime(2026, 10, 19, 8, tzinfo=zone)
    sequential = _run(
        activities, relationships, registry, workers=1, project_start=start
    )
    for workers in (2, 4):
        parallel = _run(
            activities, relationships, registry, workers=workers, project_start=start
        )
        _assert_same(sequential, parallel)
    # The span really crosses the transition.
    assert sequential.project_finish > datetime(2026, 11, 2, tzinfo=zone)


@requires_fork
def test_pipeline_matches_sequential_with_constraints():
    registry = CalendarResolverRegistry(
        time_resolvers={"site@1": TimeAwareWorkingTimeResolver(_calendar())}
    )
    activities, relationships = _network()
    constraints = (
        TimeActivityConstraint(
            activities[3].id,
            TimeConstraintType.START_NO_EARLIER_THAN,
            datetime(2026, 10, 19, 10, tzinfo=UTC),
        ),
        TimeActivityConstraint(
            activities[7].id,
            TimeConstraintType.FINISH_NO_LATER_THAN,
            datetime(2027, 3, 1, 17, tzinfo=UTC),
        ),
    )
    sequential = _run(
        activities, relationships, registry, workers=1, constraints=constraints
    )
    for workers in (2, 4):
        _assert_same(
            sequential,
            _run(activities, relationships, registry, workers=workers, constraints=constraints),
        )


@requires_fork
def test_pipeline_matches_sequential_with_actual_start_and_out_of_sequence_ss():
    registry = CalendarResolverRegistry(
        time_resolvers={"site@1": TimeAwareWorkingTimeResolver(_calendar())}
    )
    activities, relationships = _network()
    started = activities[0]
    activities = [
        TimeActivity(
            started.id,
            started.duration,
            started.calendar_context,
            actual_start=datetime(2026, 10, 13, 8, tzinfo=UTC),
        )
    ] + activities[1:]
    relationships = [
        TimeRelationship(activities[0].id, activities[1].id, RelationshipType.SS, LagQuantity.working_hours(16))
    ] + relationships[1:]
    options = TimeScheduleOptions(
        start_to_start_lag_calculation_type=StartToStartLagCalculationType.ACTUAL_START,
        data_date=datetime(2026, 10, 14, 17, tzinfo=UTC),
    )
    sequential = _run(
        activities, relationships, registry, workers=1, options=options
    )
    for workers in (2, 4):
        _assert_same(
            sequential,
            _run(activities, relationships, registry, workers=workers, options=options),
        )


@requires_fork
def test_pipeline_matches_sequential_on_every_fixture_shape():
    """Wide, fan, slack, mixed, chain and dag networks, plus a bounded finish."""

    registry = fixtures.time_registry()
    for shape in ("wide", "fan", "slack", "mixed", "chain", "dag"):
        fixture = fixtures.time_network(NETWORK_SIZE, shape)
        sequential = _run(
            fixture.activities,
            fixture.relationships,
            registry,
            workers=1,
            project_start=fixture.project_start,
            project_finish=fixture.project_finish,
        )
        for workers in (2, 4):
            _assert_same(
                sequential,
                _run(
                    fixture.activities,
                    fixture.relationships,
                    registry,
                    workers=workers,
                    project_start=fixture.project_start,
                    project_finish=fixture.project_finish,
                ),
            )
    # ``float_days`` moves the project finish past the early finish so the Free
    # Float probe searches a bounded window instead of the 9999 sentinel.
    bounded = fixtures.time_network(NETWORK_SIZE, "dag", float_days=3)
    sequential = _run(
        bounded.activities,
        bounded.relationships,
        registry,
        workers=1,
        project_start=bounded.project_start,
        project_finish=bounded.project_finish,
    )
    for workers in (2, 4):
        _assert_same(
            sequential,
            _run(
                bounded.activities,
                bounded.relationships,
                registry,
                workers=workers,
                project_start=bounded.project_start,
                project_finish=bounded.project_finish,
            ),
        )


@requires_fork
def test_pipeline_matches_sequential_when_workers_exceed_activities(single_calendar_registry):
    activities, relationships = _network(60)
    sequential = _run(activities, relationships, single_calendar_registry, workers=1)
    _assert_same(
        sequential, _run(activities, relationships, single_calendar_registry, workers=8)
    )


@requires_fork
def test_pipeline_is_deterministic_across_repeats(single_calendar_registry):
    activities, relationships = _network()
    first = _fingerprint(_run(activities, relationships, single_calendar_registry, workers=4))
    for _ in range(2):
        assert (
            _fingerprint(_run(activities, relationships, single_calendar_registry, workers=4))
            == first
        )


@requires_fork
def test_pipeline_equals_post_hoc_parallel_float_path(single_calendar_registry):
    activities, relationships = _network()
    parallel = _run(activities, relationships, single_calendar_registry, workers=4)
    sequential = _run(activities, relationships, single_calendar_registry, workers=1)
    early = sequential.early_activities
    late = sequential.late_activities
    post_hoc = calculate_time_floats(
        activities,
        relationships,
        early,
        late,
        single_calendar_registry,
        workers=4,
    )
    # The authoritative comparison: every float field of both paths is equal.
    for activity_id, item in parallel.floats.items():
        assert fixtures._iso(item.late_start) == fixtures._iso(post_hoc[activity_id].late_start)
        assert fixtures._decimal(item.total_float_value) == fixtures._decimal(
            post_hoc[activity_id].total_float_value
        )
        assert fixtures._decimal(item.free_float_value) == fixtures._decimal(
            post_hoc[activity_id].free_float_value
        )
        assert item.critical == post_hoc[activity_id].critical
    _assert_same(sequential, parallel)


# ---------------------------------------------------------------------------
# Exact fallbacks: every unsafe or unprofitable state keeps the old path
# ---------------------------------------------------------------------------


def _blocked_pool(monkeypatch):
    def explode(*args, **kwargs):
        raise AssertionError("a float pool must not be created here")

    monkeypatch.setattr(ts.multiprocessing, "get_context", explode)


def test_pipeline_falls_back_in_a_threaded_process(
    single_calendar_registry, monkeypatch
):
    activities, relationships = _network()
    sequential = _run(activities, relationships, single_calendar_registry, workers=1)
    _blocked_pool(monkeypatch)
    captured = {}

    def run():
        captured["result"] = _run(
            activities, relationships, single_calendar_registry, workers=4
        )

    worker = threading.Thread(target=run)
    worker.start()
    worker.join()
    _assert_same(sequential, captured["result"])


def test_pipeline_skips_networks_below_the_threshold(
    single_calendar_registry, monkeypatch
):
    activities, relationships = _network(40)
    sequential = _run(activities, relationships, single_calendar_registry, workers=1)

    class Exploding:
        def __init__(self, *args, **kwargs):
            raise AssertionError("pipeline used for a tiny network")

    monkeypatch.setattr(ts, "_FloatPipeline", Exploding)
    _assert_same(
        sequential, _run(activities, relationships, single_calendar_registry, workers=4)
    )


def test_pipeline_falls_back_when_admission_grants_one_slot(
    single_calendar_registry, pipeline_counter
):
    activities, relationships = _network()

    class OneSlot:
        def __enter__(self):
            return 1

        def __exit__(self, *exc):
            return False

    sequential = _run(activities, relationships, single_calendar_registry, workers=1)
    policy = FloatExecutionPolicy(workers=4, admission=lambda requested: OneSlot())
    # The fallback is the historical sequential float loop inside
    # calculate_time_floats, so no pipeline runs and no extra slot is used.
    assert (
        _fingerprint(
            _run(
                activities,
                relationships,
                single_calendar_registry,
                workers=4,
                policy=policy,
            )
        )
        == _fingerprint(sequential)
    )
    assert pipeline_counter["runs"] == 0


def test_pipeline_releases_its_guard_after_a_failure(
    single_calendar_registry, monkeypatch
):
    activities, relationships = _network()
    sequential = _run(activities, relationships, single_calendar_registry, workers=1)

    def boom(*args, **kwargs):
        raise RuntimeError("backward failure")

    monkeypatch.setattr(ts, "time_backward_pass", boom)
    with pytest.raises(RuntimeError, match="backward failure"):
        _run(activities, relationships, single_calendar_registry, workers=4)
    assert ts._FLOAT_POOL_GUARD.locked() is False
    monkeypatch.undo()
    _assert_same(
        sequential, _run(activities, relationships, single_calendar_registry, workers=4)
    )


# ---------------------------------------------------------------------------
# The hook and the shared calculation are the sequential ones
# ---------------------------------------------------------------------------


def test_on_late_hook_sees_every_activity_after_its_successors(
    single_calendar_registry,
):
    activities, relationships = _network(80)
    early = ts.time_forward_pass(
        activities,
        relationships,
        datetime(2026, 10, 12, 8, tzinfo=UTC),
        single_calendar_registry,
    )
    finish = max(item.finish for item in early.values())
    seen: list[str] = []
    late = time_backward_pass(
        activities,
        relationships,
        early,
        finish,
        single_calendar_registry,
        on_late=lambda activity_id, item: seen.append(activity_id),
    )
    assert sorted(seen) == sorted(activity.id for activity in activities)
    assert len(seen) == len(set(seen))
    position = {activity_id: index for index, activity_id in enumerate(seen)}
    for relationship in relationships:
        assert position[relationship.predecessor_id] > position[relationship.successor_id]
    assert {item.activity_id for item in late.values()} == set(seen)


def test_late_item_argument_equals_mapping_lookup(single_calendar_registry):
    activities, relationships = _network(40)
    early = ts.time_forward_pass(
        activities,
        relationships,
        datetime(2026, 10, 12, 8, tzinfo=UTC),
        single_calendar_registry,
    )
    finish = max(item.finish for item in early.values())
    late = time_backward_pass(
        activities, relationships, early, finish, single_calendar_registry
    )
    context = _time_float_context(
        activities, relationships, early, late, single_calendar_registry, None
    )
    for activity in activities:
        assert _time_float_for_activity(
            context, activity.id, late[activity.id]
        ) == _time_float_for_activity(context, activity.id)


def test_pipeline_context_without_late_map_is_never_used_for_a_value(
    single_calendar_registry,
):
    activities, relationships = _network(40)
    early = ts.time_forward_pass(
        activities,
        relationships,
        datetime(2026, 10, 12, 8, tzinfo=UTC),
        single_calendar_registry,
    )
    context = _time_float_context(
        activities, relationships, early, {}, single_calendar_registry, None
    )
    with pytest.raises(KeyError):
        _time_float_for_activity(context, activities[0].id)


def test_invalid_worker_count_is_rejected(single_calendar_registry):
    activities, relationships = _network(20)
    with pytest.raises(ValueError, match="INVALID_FLOAT_WORKERS"):
        _run(activities, relationships, single_calendar_registry, workers=0)
    with pytest.raises(ValueError, match="INVALID_FLOAT_WORKERS"):
        _run(activities, relationships, single_calendar_registry, workers=True)
    # The pipeline does not call ``calculate_time_floats``, which used to be
    # the only validator; the rejection must still happen before any work.
    with pytest.raises(ValueError, match="INVALID_FLOAT_WORKERS"):
        _run(
            activities,
            relationships,
            single_calendar_registry,
            workers=0,
            policy=FloatExecutionPolicy(workers=2),
        )


def test_pipeline_declines_when_a_pool_is_already_active(single_calendar_registry):
    activities, relationships = _network()
    assert ts._FLOAT_POOL_GUARD.acquire(blocking=False)
    try:
        context_factory = lambda: _time_float_context(
            activities, relationships, {}, {}, single_calendar_registry, None
        )
        with _float_pipeline(
            context_factory,
            activity_count=len(activities),
            workers=4,
            admission=None,
        ) as pipeline:
            assert pipeline is None
    finally:
        ts._FLOAT_POOL_GUARD.release()


def test_budget_admission_caps_the_pipeline_children(
    single_calendar_registry, pipeline_counter
):
    from construction_pm.scheduling_execution_budget import GlobalExecutionBudget
    from contextlib import contextmanager

    budget = GlobalExecutionBudget(2)
    activities, relationships = _network(400)

    @contextmanager
    def admit(requested: int):
        with budget.permit():
            with budget.admit_extra(requested) as granted:
                yield granted

    sequential = _run(activities, relationships, single_calendar_registry, workers=1)
    parallel = _run(
        activities,
        relationships,
        single_calendar_registry,
        workers=4,
        policy=FloatExecutionPolicy(workers=4, admission=admit),
    )
    _assert_same(sequential, parallel)
    assert pipeline_counter["runs"] == 1
    # Two slots total: one stays with the parent, so one child is created.
    assert budget.extra_peak <= 1
    assert budget.active == 0
