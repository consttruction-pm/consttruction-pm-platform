#!/usr/bin/env python3
"""P0-N.2: real performance and capacity evidence for the runtime-activation exit criteria.

Everything measured here is a real call to the authoritative time-aware engine
``construction_pm.scheduling.time_schedule.time_schedule`` on this host. Nothing
is extrapolated, nothing is faked, and no product code is touched: this file is
the only source added by the run.

What is measured
----------------
* Matrix: 5 activity sizes x 5 shapes, each cell run sequentially
  (``float_workers=1``) and in parallel (``slots=4`` ->
  ``FloatExecutionPolicy(workers=3, admission=make_slot_admission(4),
  allow_nested_fork=True)``). Engine wall ms, CPU seconds from ``os.times()``
  deltas, activity/relationship/constraint counts, the canonical schedule
  payload hash, and the sequential-vs-parallel hash-equality assertion.
* Capacity sweep: 25000 mixed at slots 1/2/4/8/16, speedup vs slots=1.
* Project sweep: 1/2/4/8/16 concurrent 5000-activity projects through
  ``GlobalWorkerScheduler`` with ``GlobalExecutionBudget(4)``, each job's hash
  checked against that project's own sequential hash.
* Worker end to end: a real ``SchedulingWorkerRuntime`` against real PostgreSQL
  for 1000 and 5000 activities in ``thread`` and ``process`` placement, timed
  from ``SchedulingJobService.submit`` (QUEUED) to ``SUCCEEDED`` retrieval, with
  the persisted ``output_hash`` compared to ``calculation_run_identity``.

Failure handling
----------------
Every cell runs in its own subprocess. Inside that subprocess each mode gets a
wall-clock budget enforced with ``signal.setitimer(ITIMER_REAL)``; the parent
additionally enforces a hard ``subprocess`` timeout. A cell that exceeds either
is recorded as ``TIMEOUT`` with the exact error text, never silently dropped, and
a cell that cannot be started inside the phase budget is recorded as
``SKIPPED_BUDGET`` with the exact reason. Completed cells are streamed to the
raw JSON after every run, so a killed run still leaves its evidence behind.

Usage
-----
    PYTHONPATH=src python3 scripts/p0n2_runtime_matrix.py run \
        --out-dir docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results \
        --dsn postgresql://postgres@127.0.0.1:55432/postgres

    PYTHONPATH=src python3 scripts/p0n2_runtime_matrix.py report \
        --matrix <matrix-T.json> --worker <worker-T.json> \
        --md docs/workspace/evidence/p0n-runtime-activation-2026-11-20/performance-benchmarks.md

Internal worker subcommands (``_cell``, ``_capacity``, ``_projects``, ``_worker``)
run exactly one measurement unit and write one JSON record to ``--result-file``.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SCHEMA_MATRIX = "construction-pm/p0n2-runtime-matrix/v1"
SCHEMA_WORKER = "construction-pm/p0n2-worker-e2e/v1"

ENGINE_VERSION = "cubi-26.0.0"
SEED = 20261116
SIZES = (1000, 5000, 25000, 50000, 100000)
SHAPES = ("chain", "wide", "mixed", "resource-heavy", "constraint-heavy")
MODES = ("sequential", "parallel")
PARALLEL_SLOTS = 4
CONSTRAINT_EVERY = 7
CONSTRAINT_DAY_SPAN = 21
REPEATS_SMALL = 2
REPEATS_LARGE = 1
SMALL_SIZES = (1000, 5000)

#: Per-mode wall-clock budget (seconds) inside the cell subprocess.
MODE_BUDGET_S = {1000: 60.0, 5000: 90.0, 25000: 150.0, 50000: 300.0, 100000: 180.0}
MATRIX_PHASE_DEADLINE_S = 960.0
#: Cells that must be attempted even when the phase budget is exhausted.
MATRIX_MUST_RUN = (
    (1000, "chain"), (1000, "wide"), (1000, "mixed"),
    (5000, "chain"), (5000, "wide"), (5000, "mixed"),
    (25000, "chain"), (25000, "wide"), (25000, "mixed"),
    (50000, "chain"), (50000, "wide"), (50000, "mixed"),
    (100000, "chain"), (100000, "wide"), (100000, "mixed"),
)
CELL_SLACK_S = 90.0

CAPACITY_SIZE = 25000
CAPACITY_SHAPE = "mixed"
CAPACITY_SLOTS = (1, 2, 4, 8, 16)
CAPACITY_BUDGET_S = 300.0

PROJECT_SIZE = 5000
PROJECT_SHAPE = "mixed"
PROJECT_COUNTS = (1, 2, 4, 8, 16)
PROJECT_BUDGET_SLOTS = 4
PROJECT_BUDGET_S = 600.0

WORKER_SIZES = (1000, 5000)
WORKER_MODES = ("thread", "process")
WORKER_BUDGET_S = 420.0
WORKER_DRAIN_TIMEOUT_S = 240.0

DEFAULT_DSN = (
    os.environ.get("P6_TEST_POSTGRES_DSN")
    or os.environ.get("CONSTRUCTION_PM_POSTGRES_DSN")
    or ""
).strip()


# ---------------------------------------------------------------------------
# Shapes: real fixtures only
# ---------------------------------------------------------------------------


def shape_definition(shape: str) -> str:
    if shape in ("chain", "wide", "mixed"):
        return f'time_network(size, "{shape}", seed={SEED})'
    if shape == "resource-heavy":
        return f'time_network(size, "fan", seed={SEED}) (fan: one root -> size-2 concurrent activities -> one join)'
    if shape == "constraint-heavy":
        return (
            f'time_network(size, "dag", seed={SEED}) plus TimeActivityConstraint(START_NO_EARLIER_THAN) '
            f"on every {CONSTRAINT_EVERY}th activity"
        )
    raise ValueError(f"unknown shape {shape!r}")


@dataclass(frozen=True)
class CellFixture:
    """``(activities, relationships, registry, start, finish, constraints)`` plus counts."""

    activities: tuple
    relationships: tuple
    registry: object
    project_start: datetime
    project_finish: object
    constraints: tuple


def build_cell(size: int, shape: str, seed: int = SEED) -> CellFixture:
    from construction_pm.scheduling.benchmark_fixtures import activity_id, time_network
    from construction_pm.scheduling.time_constraints import (
        TimeActivityConstraint,
        TimeConstraintType,
    )
    from construction_pm.scheduling.benchmark_fixtures import TIME_PROJECT_START

    if shape in ("chain", "wide", "mixed"):
        base = time_network(size, shape, seed)
        return CellFixture(base.activities, base.relationships, base.registry,
                           base.project_start, base.project_finish, ())
    if shape == "resource-heavy":
        base = time_network(size, "fan", seed)
        return CellFixture(base.activities, base.relationships, base.registry,
                           base.project_start, base.project_finish, ())
    if shape == "constraint-heavy":
        base = time_network(size, "dag", seed)
        constraints = tuple(
            TimeActivityConstraint(
                activity_id(index),
                TimeConstraintType.START_NO_EARLIER_THAN,
                TIME_PROJECT_START
                + timedelta(days=(index % CONSTRAINT_DAY_SPAN) + 1),
            )
            for index in range(0, size, CONSTRAINT_EVERY)
        )
        return CellFixture(base.activities, base.relationships, base.registry,
                           base.project_start, base.project_finish, constraints)
    raise ValueError(f"unknown shape {shape!r}")


def parallel_policy(slots: int):
    from construction_pm.scheduling.time_schedule import FloatExecutionPolicy
    from construction_pm.scheduling_worker_scheduler import make_slot_admission

    workers = max(1, slots - 1)
    return FloatExecutionPolicy(
        workers=workers,
        admission=make_slot_admission(slots),
        allow_nested_fork=True,
    )


# ---------------------------------------------------------------------------
# Measurement primitives
# ---------------------------------------------------------------------------


class ModeTimeout(Exception):
    pass


class _TimeoutHandler:
    """SIGALRM-based wall-clock budget around one engine call."""

    def __init__(self, seconds: float) -> None:
        self.seconds = float(seconds)

    def __enter__(self) -> "_TimeoutHandler":
        def _fire(signum, frame):  # noqa: ARG001 - signal signature
            raise ModeTimeout(f"TIMEOUT after {self.seconds:.1f}s wall clock")

        self.previous = signal.signal(signal.SIGALRM, _fire)
        signal.setitimer(signal.ITIMER_REAL, self.seconds)
        return self

    def __exit__(self, *exc: object) -> None:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, self.previous)


def cpu_delta(before, after) -> float:
    return max(
        0.0,
        float(
            (after.user + after.system + after.children_user + after.children_system)
            - (before.user + before.system + before.children_user + before.children_system)
        ),
    )


def measure_once(fixture: CellFixture, mode: str, slots: int = PARALLEL_SLOTS):
    """One real engine call: wall ms, CPU seconds, payload hash, finish, counts."""
    from construction_pm.scheduling.benchmark_fixtures import (
        canonical_hash,
        time_schedule_payload,
    )
    from construction_pm.scheduling.time_schedule import time_schedule

    if mode == "sequential":
        workers, policy = 1, None
    elif mode == "parallel":
        workers = max(1, slots - 1)
        policy = parallel_policy(slots)
    else:
        raise ValueError(f"unknown mode {mode!r}")

    cpu_before = os.times()
    started = time.perf_counter()
    result = time_schedule(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.project_finish,
        fixture.registry,
        fixture.constraints,
        float_workers=workers,
        float_policy=policy,
    )
    engine_ms = (time.perf_counter() - started) * 1000.0
    cpu_seconds = cpu_delta(cpu_before, os.times())
    payload = time_schedule_payload(result)
    digest = canonical_hash(payload)
    floats = list(result.floats.values())
    total_hours = [float(item.total_float_hours) for item in floats] or [0.0]
    return {
        "engine_ms": round(engine_ms, 1),
        "cpu_seconds": round(cpu_seconds, 3),
        "hash": digest,
        "project_finish": result.project_finish.isoformat(),
        "critical_count": sum(1 for item in floats if getattr(item, "critical", False)),
        "min_total_float_hours": round(min(total_hours), 3),
        "max_total_float_hours": round(max(total_hours), 3),
    }


def median(values: list):
    import statistics

    return round(statistics.median(values), 1) if values else None


# ---------------------------------------------------------------------------
# Subprocess unit: one matrix cell (both modes)
# ---------------------------------------------------------------------------


def run_cell_unit(
    size: int, shape: str, deadline: float, mode_budget: float | None = None
) -> dict:
    """Run one cell sequentially and in parallel inside this process.

    ``mode_budget`` overrides ``MODE_BUDGET_S`` for a single cell. It exists so a
    size whose measured run exceeds the default budget can still be measured
    instead of being reported from an assumption.
    """
    from construction_pm.scheduling.benchmark_fixtures import environment_fingerprint

    record: dict = {
        "size": size,
        "shape": shape,
        "shape_definition": shape_definition(shape),
        "seed": SEED,
        "repeats": REPEATS_SMALL if size in SMALL_SIZES else REPEATS_LARGE,
        "parallel_slots": PARALLEL_SLOTS,
        "mode_budget_override_s": mode_budget,
        "modes": {},
        "status": "OK",
        "error": None,
    }
    fixture_budget = max(10.0, min(120.0, deadline - time.time()))
    try:
        with _TimeoutHandler(fixture_budget):
            built_at = time.perf_counter()
            fixture = build_cell(size, shape)
            record["fixture_ms"] = round((time.perf_counter() - built_at) * 1000.0, 1)
    except ModeTimeout as error:
        record["status"] = "TIMEOUT"
        record["error"] = f"fixture build {error}"
        record["hash_equality"] = {"status": "NOT_EVALUABLE", "reason": record["error"]}
        return record

    record["activities"] = len(fixture.activities)
    record["relationships"] = len(fixture.relationships)
    record["constraints"] = len(fixture.constraints)

    for mode in MODES:
        remaining = deadline - time.time()
        if remaining <= 5.0:
            record["modes"][mode] = {
                "status": "TIMEOUT",
                "error": f"TIMEOUT: no phase budget left for {mode} (remaining {remaining:.1f}s)",
                "runs": [],
                "budget_s": round(max(0.0, remaining), 1),
            }
            continue
        budget = min(
            MODE_BUDGET_S[size] if mode_budget is None else float(mode_budget),
            remaining,
        )
        runs = []
        status, error = "OK", None
        try:
            with _TimeoutHandler(budget):
                for index in range(record["repeats"]):
                    runs.append(measure_once(fixture, mode))
        except ModeTimeout as exc:
            status, error = "TIMEOUT", str(exc)
        except Exception as exc:  # noqa: BLE001 - reported, never hidden
            status, error = "ERROR", f"{type(exc).__name__}: {exc}"
        hashes = [run["hash"] for run in runs]
        record["modes"][mode] = {
            "status": status,
            "error": error,
            "budget_s": round(budget, 1),
            "float_workers": 1 if mode == "sequential" else max(1, PARALLEL_SLOTS - 1),
            "policy": (
                "float_workers=1, no policy"
                if mode == "sequential"
                else f"FloatExecutionPolicy(workers={max(1, PARALLEL_SLOTS - 1)}, "
                     f"admission=make_slot_admission({PARALLEL_SLOTS}), allow_nested_fork=True)"
            ),
            "runs": runs,
            "engine_ms_median": median([run["engine_ms"] for run in runs]),
            "cpu_seconds_total": round(sum(run["cpu_seconds"] for run in runs), 3),
            "hash": hashes[0] if hashes else None,
            "internal_hash_agreement": bool(hashes) and len(set(hashes)) == 1,
        }
        if status != "OK":
            record["status"] = status
            record["error"] = f"{mode}: {error}"

    seq, par = record["modes"]["sequential"], record["modes"]["parallel"]
    if seq["status"] == "OK" and par["status"] == "OK":
        same = seq["hash"] == par["hash"]
        record["hash_equality"] = {
            "status": "PASS" if same else "FAILED",
            "sequential_hash": seq["hash"],
            "parallel_hash": par["hash"],
            "sequential_hashes": [run["hash"] for run in seq["runs"]],
            "parallel_hashes": [run["hash"] for run in par["runs"]],
            "error": None if same else f"HASH MISMATCH sequential={seq['hash']} parallel={par['hash']}",
        }
        if not same:
            record["status"] = "FAILED"
            record["error"] = record["hash_equality"]["error"]
    else:
        record["hash_equality"] = {
            "status": "NOT_EVALUABLE",
            "sequential_hash": seq.get("hash"),
            "parallel_hash": par.get("hash"),
            "reason": "one or both modes did not complete",
        }
    record["environment"] = environment_fingerprint()
    return record


# ---------------------------------------------------------------------------
# Subprocess unit: capacity sweep point
# ---------------------------------------------------------------------------


def run_capacity_unit(slots: int, deadline: float) -> dict:
    from construction_pm.scheduling.benchmark_fixtures import environment_fingerprint

    record = {
        "size": CAPACITY_SIZE,
        "shape": CAPACITY_SHAPE,
        "shape_definition": shape_definition(CAPACITY_SHAPE),
        "slots": slots,
        "float_workers": max(1, slots - 1),
        "policy": f"FloatExecutionPolicy(workers={max(1, slots - 1)}, "
                  f"admission=make_slot_admission({slots}), allow_nested_fork=True)",
        "status": "OK",
        "error": None,
    }
    try:
        with _TimeoutHandler(max(10.0, min(150.0, deadline - time.time()))):
            fixture = build_cell(CAPACITY_SIZE, CAPACITY_SHAPE)
        record["activities"] = len(fixture.activities)
        record["relationships"] = len(fixture.relationships)
        with _TimeoutHandler(max(5.0, deadline - time.time())):
            run = measure_once(fixture, "parallel" if slots > 1 else "sequential", slots)
        record.update(run)
    except ModeTimeout as error:
        record["status"] = "TIMEOUT"
        record["error"] = str(error)
    except Exception as error:  # noqa: BLE001
        record["status"] = "ERROR"
        record["error"] = f"{type(error).__name__}: {error}"
    record["environment"] = environment_fingerprint()
    return record


# ---------------------------------------------------------------------------
# Subprocess unit: project sweep through GlobalWorkerScheduler
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectSpec:
    name: str
    size: int
    shape: str
    seed: int
    tenant: str


def run_project(spec: ProjectSpec, slots: int) -> dict:
    """The job body handed to the scheduler; runs inside the job's own process."""
    from construction_pm.scheduling.benchmark_fixtures import (
        canonical_hash,
        time_schedule_payload,
    )
    from construction_pm.scheduling.time_schedule import time_schedule

    fixture = build_cell(spec.size, spec.shape, spec.seed)
    workers = max(1, slots - 1)
    policy = parallel_policy(slots)
    cpu_before = os.times()
    started = time.perf_counter()
    result = time_schedule(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.project_finish,
        fixture.registry,
        fixture.constraints,
        float_workers=workers,
        float_policy=policy,
    )
    engine_ms = (time.perf_counter() - started) * 1000.0
    return {
        "hash": canonical_hash(time_schedule_payload(result)),
        "activities": len(fixture.activities),
        "relationships": len(fixture.relationships),
        "slots": slots,
        "float_workers": workers,
        "engine_ms": round(engine_ms, 1),
        "cpu_seconds": round(cpu_delta(cpu_before, os.times()), 3),
    }


def run_projects_unit(count: int, deadline: float) -> dict:
    import multiprocessing

    from construction_pm.scheduling.benchmark_fixtures import environment_fingerprint
    from construction_pm.scheduling_execution_budget import GlobalExecutionBudget
    from construction_pm.scheduling_worker_scheduler import (
        GlobalWorkerScheduler,
        ProjectWorkload,
    )

    stamp = uuid.uuid4().hex[:8]
    specs = [
        ProjectSpec(
            name=f"P{index:02d}",
            size=PROJECT_SIZE,
            shape=PROJECT_SHAPE,
            seed=SEED + index,
            tenant=f"T-p0n2-{stamp}-{index:02d}",
        )
        for index in range(count)
    ]
    record: dict = {
        "projects": count,
        "size": PROJECT_SIZE,
        "shape": PROJECT_SHAPE,
        "shape_definition": shape_definition(PROJECT_SHAPE),
        "seeds": [spec.seed for spec in specs],
        "budget_workers": PROJECT_BUDGET_SLOTS,
        "status": "OK",
        "error": None,
    }

    # Sequential reference hashes: one per distinct project network.
    reference: dict[str, str] = {}
    counts: dict[str, tuple[int, int]] = {}
    reference_started = time.perf_counter()
    try:
        for spec in specs:
            fixture = build_cell(spec.size, spec.shape, spec.seed)
            counts[spec.name] = (len(fixture.activities), len(fixture.relationships))
            reference[spec.name] = measure_once(fixture, "sequential")["hash"]
        record["sequential_reference_ms_total"] = round(
            (time.perf_counter() - reference_started) * 1000.0, 1
        )
    except Exception as error:  # noqa: BLE001
        record["status"] = "ERROR"
        record["error"] = f"sequential reference: {type(error).__name__}: {error}"
    record["sequential_reference_hashes"] = dict(reference)

    if record["status"] == "OK":
        scheduler = GlobalWorkerScheduler(
            budget=GlobalExecutionBudget(PROJECT_BUDGET_SLOTS), poll_interval=0.005
        )
        started = time.perf_counter()
        for spec in specs:
            activities, relationships = counts[spec.name]
            scheduler.submit(
                f"p0n2-{stamp}-{spec.name}",
                partial(run_project, spec),
                workload=ProjectWorkload(activities, relationships),
                tenant_id=spec.tenant,
            )
        error = None
        try:
            scheduler.run_until_idle(
                timeout=max(5.0, min(PROJECT_BUDGET_S, deadline - time.time()))
            )
        except Exception as failure:  # noqa: BLE001
            error = f"{type(failure).__name__}: {failure}"
        wall = time.perf_counter() - started
        snapshot = scheduler.snapshot()
        jobs = []
        hashes_ok = True
        for row in scheduler.results():
            key = str(row["key"])
            name = key.rsplit("-", 1)[1]
            value = scheduler.value_for(key)
            actual = value.get("hash") if isinstance(value, dict) else None
            expected = reference.get(name)
            match = expected is not None and actual == expected
            hashes_ok = hashes_ok and match
            jobs.append(
                {
                    "project": name,
                    "seed": next(s.seed for s in specs if s.name == name),
                    "tenant": next(s.tenant for s in specs if s.name == name),
                    "state": row["state"],
                    "slots": row["slots"],
                    "queue_wait_ms": None if row["queue_wait_ms"] is None else round(float(row["queue_wait_ms"]), 1),
                    "run_ms": None if row["run_ms"] is None else round(float(row["run_ms"]), 1),
                    "cpu_seconds": row["cpu_seconds"],
                    "engine_ms": None if not isinstance(value, dict) else value.get("engine_ms"),
                    "sequential_hash": expected,
                    "scheduled_hash": actual,
                    "hash_match": match,
                    "error": row["error"],
                }
            )
        record.update(
            {
                "wall_ms": round(wall * 1000.0, 1),
                "start_method": scheduler.start_method,
                "multiprocessing_start_methods": multiprocessing.get_all_start_methods(),
                "error": error,
                "hashes_match": hashes_ok and len(jobs) == count and error is None,
                "peak_slots": snapshot.get("peak_slots"),
                "slots_acquired_total": snapshot.get("slots_acquired_total"),
                "process_starts": snapshot.get("process_starts"),
                "inline_fallbacks": snapshot.get("inline_fallbacks"),
                "budget_active_after": scheduler.budget.active,
                "jobs": jobs,
                "queue_wait_ms_max": max(
                    (j["queue_wait_ms"] for j in jobs if j["queue_wait_ms"] is not None),
                    default=None,
                ),
                "throughput_projects_per_s": round(count / wall, 3) if wall else None,
            }
        )
        if error is not None:
            record["status"] = "ERROR"
    record["environment"] = environment_fingerprint()
    return record


# ---------------------------------------------------------------------------
# Subprocess unit: real worker end to end on PostgreSQL
# ---------------------------------------------------------------------------


def seed_ready_scope(connection, activity_count: int):
    """Minimal copy of tests/integration/test_p0n2_runtime_activation.py seeding.

    One unique tenant/project scope, one working-day calendar plus its snapshot,
    and one DATE_BASED input snapshot with ``activity_count`` activities.
    """
    from construction_pm.backend_p0.models import BackendScope
    from construction_pm.calendar_exception_repository import (
        PostgresCalendarExceptionRepository,
    )
    from construction_pm.calendar_master_repository import (
        CalendarMaster,
        PostgresCalendarMasterRepository,
    )
    from construction_pm.calendar_snapshot_repository import (
        PostgresCalendarSnapshotRepository,
    )
    from construction_pm.calendar_work_hours_repository import (
        PostgresCalendarWorkHourRepository,
    )
    from construction_pm.schedule_calculation_context_repository import (
        PostgresCalculationContextRepository,
        build_persisted_context,
    )
    from construction_pm.schedule_input_snapshot_repository import (
        PostgresScheduleInputSnapshotRepository,
        build_snapshot,
    )
    from construction_pm.scheduling.activity import Activity
    from construction_pm.scheduling.authoritative_schedule import (
        AuthoritativeScheduleInput,
        AuthoritativeScheduleMode,
    )
    from construction_pm.scheduling.calculation_context import CalculationContext
    from construction_pm.scheduling.calendar import WorkingCalendar
    from construction_pm.scheduling.calendar_context import CalendarReference

    suffix = uuid.uuid4().hex[:10]
    scope = BackendScope(f"T-p0n2-{suffix}", f"P-p0n2-{suffix}", 0)
    for repository in (
        PostgresCalendarMasterRepository(connection),
        PostgresCalendarSnapshotRepository(connection),
        PostgresCalendarWorkHourRepository(connection),
        PostgresCalendarExceptionRepository(connection),
    ):
        repository.initialize()
    master = PostgresCalendarMasterRepository(connection).save(
        CalendarMaster(scope, "CAL-1", "1", "working-day", "CAL-1 calendar")
    )
    PostgresCalendarSnapshotRepository(connection).save(master, WorkingCalendar())

    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    snapshot_id = f"S-{uuid.uuid4().hex}"
    source = AuthoritativeScheduleInput(
        snapshot_id=snapshot_id,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
        project_revision=scope.project_revision,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL-1", "1"),
        activities=tuple(
            Activity(f"A{index:05d}", 2) for index in range(activity_count)
        ),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id=scope.project_id,
        project_version=scope.project_revision,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp=now.isoformat(),
        input_snapshot_id=snapshot_id,
        tenant_id=scope.tenant_id,
        actor_id="authoritative-actor",
    )
    snapshots = PostgresScheduleInputSnapshotRepository(connection)
    contexts = PostgresCalculationContextRepository(connection)
    snapshots.initialize()
    contexts.initialize()
    saved_at = time.perf_counter()
    snapshots.save(build_snapshot(source, context, now))
    snapshot_save_ms = round((time.perf_counter() - saved_at) * 1000.0, 1)
    contexts.save(build_persisted_context(scope, context))
    return scope, snapshot_id, snapshot_save_ms


def run_worker_unit(dsn: str, size: int, mode: str, deadline: float) -> dict:
    import psycopg

    from construction_pm.deployment.scheduling_worker import (
        SchedulingWorkerRuntime,
        SchedulingWorkerSettings,
    )
    from construction_pm.postgres_scheduling_job_lifecycle import (
        PostgresSchedulingJobRepository,
    )
    from construction_pm.schedule_input_snapshot_repository import (
        PostgresScheduleInputSnapshotRepository,
    )
    from construction_pm.scheduling.benchmark_fixtures import environment_fingerprint
    from construction_pm.scheduling_job_api import SchedulingJobAPI, SchedulingJobScope
    from construction_pm.scheduling_job_lifecycle import SchedulingJobService

    record: dict = {
        "size": size,
        "execution_mode": mode,
        "dsn": dsn,
        "worker_settings": {
            "slots": 2,
            "poll_interval": 0.25,
            "job_timeout": None,
            "connect_timeout": 10,
        },
        "status": "OK",
        "error": None,
    }
    connection = psycopg.connect(dsn, autocommit=True, connect_timeout=10)
    worker = None
    try:
        with _TimeoutHandler(max(10.0, min(180.0, deadline - time.time()))):
            scope, snapshot_id, snapshot_save_ms = seed_ready_scope(connection, size)
        record["tenant_id"] = scope.tenant_id
        record["project_id"] = scope.project_id
        record["snapshot_id"] = snapshot_id
        record["snapshot_save_ms"] = snapshot_save_ms

        repository = PostgresSchedulingJobRepository(connection)
        repository.initialize()
        service = SchedulingJobService(repository)
        api = SchedulingJobAPI(
            service, snapshot_repository=PostgresScheduleInputSnapshotRepository(connection)
        )
        job_scope = SchedulingJobScope(
            scope.tenant_id,
            scope.project_id,
            scope.project_revision,
            "bench",
            frozenset({"project_admin"}),
        )
        submitted_at = time.perf_counter()
        view = api.submit(job_scope, snapshot_id=snapshot_id)
        submit_ms = round((time.perf_counter() - submitted_at) * 1000.0, 1)
        record["job_id"] = view.job.job_id
        record["state_after_submit"] = view.job.state.value
        record["calculation_identity"] = view.job.calculation_identity
        record["submit_ms"] = submit_ms

        worker = SchedulingWorkerRuntime(
            SchedulingWorkerSettings(
                database_url=dsn,
                execution_mode=mode,
                slots=2,
                owner=f"p0n2-bench-{mode}-{size}-{scope.tenant_id[-6:]}",
                poll_interval=0.25,
            )
        )
        drained_at = time.perf_counter()
        outcome = worker.drain(timeout=WORKER_DRAIN_TIMEOUT_S)
        drain_ms = round((time.perf_counter() - drained_at) * 1000.0, 1)
        record["drain_ms"] = drain_ms
        record["outcome"] = outcome.as_dict()
        record["worker_snapshot"] = worker.snapshot()

        finished_at = time.perf_counter()
        job = service.get(
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
            job_id=view.job.job_id,
            user_id="bench",
        )
        result = service.get_result(
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
            job_id=view.job.job_id,
            user_id="bench",
        )
        record["retrieval_ms"] = round((time.perf_counter() - finished_at) * 1000.0, 1)
        record["state"] = job.state.value
        record["attempts"] = job.attempts
        record["lease_owner"] = job.lease_owner
        record["last_error"] = job.last_error
        record["output_hash"] = result.output_hash
        record["calculation_run_identity"] = result.payload.get("calculation_run_identity")
        record["result_activity_count"] = result.payload.get("activity_count")
        record["job_created_at"] = job.created_at.isoformat()
        record["job_updated_at"] = job.updated_at.isoformat()
        record["persisted_at"] = result.persisted_at.isoformat()
        record["db_submit_to_succeeded_ms"] = round(
            (job.updated_at - job.created_at).total_seconds() * 1000.0, 1
        )
        record["e2e_ms"] = round((finished_at - submitted_at) * 1000.0, 1)
        record["hash_match"] = result.output_hash == record["calculation_run_identity"]
        if job.state.value != "SUCCEEDED":
            record["status"] = "FAILED"
            record["error"] = f"job state {job.state.value} (last_error={job.last_error})"
        elif not record["hash_match"]:
            record["status"] = "FAILED"
            record["error"] = (
                f"OUTPUT_HASH_MISMATCH output_hash={result.output_hash} "
                f"calculation_run_identity={record['calculation_run_identity']}"
            )
    except ModeTimeout as error:
        record["status"] = "TIMEOUT"
        record["error"] = str(error)
    except Exception as error:  # noqa: BLE001
        record["status"] = "ERROR"
        record["error"] = f"{type(error).__name__}: {error}"
    finally:
        if worker is not None:
            try:
                worker.close()
            except Exception:  # noqa: BLE001
                pass
        try:
            connection.close()
        except Exception:  # noqa: BLE001
            pass
    record["environment"] = environment_fingerprint()
    return record


# ---------------------------------------------------------------------------
# Subprocess entry points
# ---------------------------------------------------------------------------


def child_main(arguments: argparse.Namespace) -> int:
    if arguments.unit == "_cell":
        record = run_cell_unit(
            arguments.size, arguments.shape, arguments.deadline,
            getattr(arguments, "mode_budget", None),
        )
    elif arguments.unit == "_capacity":
        record = run_capacity_unit(arguments.slots, arguments.deadline)
    elif arguments.unit == "_projects":
        record = run_projects_unit(arguments.count, arguments.deadline)
    elif arguments.unit == "_worker":
        record = run_worker_unit(arguments.dsn, arguments.size, arguments.mode, arguments.deadline)
    else:  # pragma: no cover - argparse choices
        raise SystemExit(f"unknown unit {arguments.unit}")
    payload = json.dumps(record, default=str).encode("utf-8")
    Path(arguments.result_file).write_bytes(payload)
    print(json.dumps({"unit": arguments.unit.lstrip("_"), "status": record.get("status")}))
    return 0 if record.get("status") in (None, "OK", "TIMEOUT", "FAILED", "ERROR") else 1


# ---------------------------------------------------------------------------
# Parent orchestration
# ---------------------------------------------------------------------------


def child_environment(dsn: str) -> dict:
    env = dict(os.environ)
    src = str(ROOT / "src")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src if not existing else f"{src}{os.pathsep}{existing}"
    if dsn:
        env["P6_TEST_POSTGRES_DSN"] = dsn
        env["CONSTRUCTION_PM_POSTGRES_DSN"] = dsn
    return env


class LogWriter:
    def __init__(self, path: Path, echo: bool = True) -> None:
        self.path = path
        self.echo = echo
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    def write(self, text: str) -> None:
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(text)
        if self.echo:
            sys.stdout.write(text)
            sys.stdout.flush()


def run_child(cmd: list[str], result_file: Path, log: LogWriter, hard_timeout: float, env: dict):
    command_line = " ".join(cmd)
    started = time.perf_counter()
    status = "OK"
    error = None
    stdout = stderr = ""
    returncode = None
    record = None
    if result_file.exists():
        result_file.unlink()
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=hard_timeout,
            env=env,
            cwd=str(ROOT),
            check=False,
        )
        returncode = completed.returncode
        stdout, stderr = completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as timeout_error:
        status = "TIMEOUT"
        error = (
            f"TIMEOUT: subprocess exceeded hard wall-clock limit {hard_timeout:.1f}s; "
            f"stdout={str(timeout_error.stdout)[:400]!r} stderr={str(timeout_error.stderr)[:400]!r}"
        )
    except Exception as failure:  # noqa: BLE001
        status = "ERROR"
        error = f"{type(failure).__name__}: {failure}"
    if result_file.exists():
        try:
            record = json.loads(result_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as failure:
            status = "ERROR"
            error = f"RESULT_JSON_INVALID: {failure}"
    if record is not None and record.get("status") in ("TIMEOUT", "FAILED", "ERROR"):
        status = record["status"]
        error = record.get("error")
    wall_ms = round((time.perf_counter() - started) * 1000.0, 1)
    log.write(
        f"\n$ {command_line}\n"
        f"[{status}] wall_ms={wall_ms} exit={returncode}\n"
        f"--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}\n"
    )
    if result_file.exists():
        result_file.unlink()
    return record, {"command": command_line, "status": status, "error": error,
                    "wall_ms": wall_ms, "exit": returncode,
                    "stdout": stdout, "stderr": stderr}


def postgres_version(dsn: str) -> str | None:
    try:
        import psycopg

        connection = psycopg.connect(dsn, autocommit=True, connect_timeout=10)
        try:
            return connection.execute("select version()").fetchone()[0]
        finally:
            connection.close()
    except Exception as failure:  # noqa: BLE001
        return f"UNAVAILABLE: {type(failure).__name__}: {failure}"


def git_information() -> dict:
    commands = {
        "commit": ["git", "rev-parse", "HEAD"],
        "branch": ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        "working_tree_porcelain": ["git", "status", "--porcelain"],
    }
    out: dict = {}
    for key, command in commands.items():
        try:
            out[key] = subprocess.run(
                command, capture_output=True, text=True, cwd=str(ROOT), check=False,
            ).stdout.strip()
        except Exception as failure:  # noqa: BLE001
            out[key] = f"UNAVAILABLE: {failure}"
    return out


def atomic_write(path: Path, payload: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(temp, path)


def ordered_cells() -> list[tuple[int, str]]:
    return [(size, shape) for size in SIZES for shape in SHAPES]


def orchestrate(arguments: argparse.Namespace) -> int:
    from construction_pm.scheduling.benchmark_fixtures import environment_fingerprint

    started_at = datetime.now(timezone.utc)
    stamp = started_at.strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(arguments.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = out_dir / f"matrix-{stamp}.json"
    log_path = out_dir / f"matrix-{stamp}.log"
    worker_path = out_dir / f"worker-e2e-{stamp}.json"
    scratch = out_dir / f".unit-{stamp}"
    scratch.mkdir(parents=True, exist_ok=True)

    log = LogWriter(log_path)
    dsn = arguments.dsn
    env = child_environment(dsn)
    fingerprint = environment_fingerprint(git_information().get("commit"))
    log.write(
        f"P0-N.2 runtime matrix run started {started_at.isoformat()}\n"
        f"command: {' '.join(sys.argv)}\n"
        f"cwd: {os.getcwd()}\nrepo: {ROOT}\n"
        f"environment: {json.dumps(fingerprint, default=str)}\n"
        f"python: {sys.version.split()[0]}\ncpu_count: {os.cpu_count()}\n"
        f"cpu_affinity: {len(os.sched_getaffinity(0))}\n"
        f"postgres: {postgres_version(dsn) if dsn else 'NO DSN'}\n"
        f"mode budgets: {MODE_BUDGET_S} parallel_slots: {PARALLEL_SLOTS}\n"
    )

    document: dict = {
        "schema": SCHEMA_MATRIX,
        "generated_at": started_at.isoformat(),
        "started_at": started_at.isoformat(),
        "repo_root": str(ROOT),
        "git": git_information(),
        "environment": fingerprint,
        "postgres_version": postgres_version(dsn) if dsn else None,
        "argv": sys.argv,
        "definitions": {
            "sizes": list(SIZES),
            "shapes": list(SHAPES),
            "shape_definitions": {shape: shape_definition(shape) for shape in SHAPES},
            "seed": SEED,
            "constraint_target_formula": (
                "TIME_PROJECT_START + timedelta(days=(index % "
                f"{CONSTRAINT_DAY_SPAN}) + 1) for index in range(0, size, {CONSTRAINT_EVERY})"
            ),
            "project_finish_source": "fixture project_finish from time_network (float_days=0)",
            "sequential": "time_schedule(..., float_workers=1, float_policy=None)",
            "parallel": (
                f"time_schedule(..., float_workers={PARALLEL_SLOTS - 1}, float_policy="
                f"FloatExecutionPolicy(workers={PARALLEL_SLOTS - 1}, "
                f"admission=make_slot_admission({PARALLEL_SLOTS}), allow_nested_fork=True))"
            ),
            "repeats": {"small": REPEATS_SMALL, "large": REPEATS_LARGE,
                        "small_sizes": list(SMALL_SIZES)},
            "mode_budget_s": {str(k): v for k, v in MODE_BUDGET_S.items()},
            "matrix_phase_deadline_s": MATRIX_PHASE_DEADLINE_S,
            "timeout_policy": (
                "each cell runs in its own subprocess; every mode is bounded by "
                "signal.setitimer(ITIMER_REAL) inside the child and a hard subprocess "
                "timeout in the parent; a cell with no phase budget left is recorded "
                "SKIPPED_BUDGET"
            ),
            "engine_module": "construction_pm.scheduling.time_schedule.time_schedule",
            "notes": [
                "Measurement only: this harness adds scripts/p0n2_runtime_matrix.py and "
                "the four evidence files under "
                "docs/workspace/evidence/p0n-runtime-activation-2026-11-20/ and changes no "
                "product code, test, or configuration.",
                "The worker process-mode path runs against "
                "src/construction_pm/scheduling_job_executor.py as it stands in this working "
                "tree, which carries an uncommitted fix from another work item: the parent now "
                "drains the result pipe (non-blocking poll/recv) before joining the child. "
                "Before that fix, two exploratory 5000-activity process-mode runs started by "
                "this harness deadlocked with the job child blocked in pipe_write once the "
                "pickled SchedulingJobResult exceeded the ~64 KB pipe buffer; those runs were "
                "terminated, are not part of this evidence, and their job rows were left as "
                "found (expired LEASED, cancelled by the fixing work item).",
                "constraint-heavy cells pass the fixture's own (unconstrained) project_finish "
                "to time_schedule, exactly like "
                "scripts/p0n_multi_project_benchmark.py::run_project. Because the "
                "START_NO_EARLIER_THAN list pushes work later than that finish, the recorded "
                "total float for those cells is negative; "
                "min_total_float_hours/max_total_float_hours are stored per run so the effect "
                "is visible instead of hidden.",
                "This host runs other work items in parallel; the same PostgreSQL instance is "
                "shared. Each worker run seeds its own unique tenant scope, so rows never "
                "overlap, but wall-clock numbers can include contention noise.",
            ],
        },
        "matrix_cells": [],
        "capacity_sweep": [],
        "project_sweep": [],
        "runs": [],
        "status": "RUNNING",
    }
    atomic_write(matrix_path, document)

    script = str(Path(__file__).resolve())

    def spawn(unit: list[str], name: str, hard_timeout: float) -> tuple:
        result_file = scratch / f"{name}.json"
        cmd = [sys.executable, script, *unit, "--result-file", str(result_file)]
        return run_child(cmd, result_file, log, hard_timeout, env)

    # -- matrix -----------------------------------------------------------
    matrix_start = time.monotonic()
    cells = ordered_cells()
    for index, (size, shape) in enumerate(cells):
        phase_remaining = MATRIX_PHASE_DEADLINE_S - (time.monotonic() - matrix_start)
        must = (size, shape) in MATRIX_MUST_RUN
        budget = MODE_BUDGET_S[size]
        if phase_remaining <= 20.0 and not must:
            record = {
                "size": size,
                "shape": shape,
                "shape_definition": shape_definition(shape),
                "seed": SEED,
                "status": "SKIPPED_BUDGET",
                "error": (
                    f"SKIPPED_BUDGET: matrix phase budget {MATRIX_PHASE_DEADLINE_S:.0f}s exhausted; "
                    f"remaining {phase_remaining:.1f}s at cell ({size},{shape})"
                ),
                "modes": {},
                "hash_equality": {"status": "NOT_EVALUABLE", "reason": "cell not run"},
            }
            document["matrix_cells"].append(record)
            document["runs"].append({"unit": "cell", "command": "(not spawned)",
                                     "status": "SKIPPED_BUDGET", "error": record["error"]})
            atomic_write(matrix_path, document)
            log.write(f"SKIPPED_BUDGET cell size={size} shape={shape} remaining={phase_remaining:.1f}s\n")
            continue
        allowance = 2 * budget + CELL_SLACK_S
        if not must:
            allowance = min(allowance, max(30.0, phase_remaining + 20.0))
        deadline = time.time() + allowance
        hard_timeout = allowance + 15.0
        record, run_info = spawn(
            ["_cell", "--size", str(size), "--shape", shape, "--deadline", f"{deadline:.3f}"],
            f"cell-{index:02d}-{size}-{shape}",
            hard_timeout,
        )
        if record is None:
            record = {
                "size": size, "shape": shape,
                "shape_definition": shape_definition(shape),
                "status": run_info["status"], "error": run_info["error"],
                "modes": {}, "hash_equality": {"status": "NOT_EVALUABLE",
                                               "reason": run_info["error"]},
            }
        record["unit_run"] = run_info
        document["matrix_cells"].append(record)
        document["runs"].append({"unit": "cell", **run_info})
        atomic_write(matrix_path, document)

    # -- capacity ---------------------------------------------------------
    reference_hash = None
    for cell in document["matrix_cells"]:
        if cell.get("size") == CAPACITY_SIZE and cell.get("shape") == CAPACITY_SHAPE:
            parallel = (cell.get("modes") or {}).get("parallel") or {}
            reference_hash = parallel.get("hash")
    for slots in CAPACITY_SLOTS:
        record, run_info = spawn(
            ["_capacity", "--slots", str(slots),
             "--deadline", f"{time.time() + CAPACITY_BUDGET_S:.3f}"],
            f"capacity-{slots}",
            CAPACITY_BUDGET_S + 60.0,
        )
        record = record or {"slots": slots, "status": run_info["status"],
                            "error": run_info["error"]}
        record["unit_run"] = run_info
        record["reference_matrix_parallel_hash"] = reference_hash
        record["hash_equals_matrix_cell"] = (
            record.get("hash") == reference_hash if record.get("hash") and reference_hash else None
        )
        record["phase"] = "capacity_sweep"
        if slots == CAPACITY_SLOTS[0]:
            record["speedup_vs_slots_1"] = 1.0
        document["capacity_sweep"].append(record)
        document["runs"].append({"unit": "capacity", **run_info})
        atomic_write(matrix_path, document)
    base = next(
        (c.get("engine_ms") for c in document["capacity_sweep"] if c.get("slots") == 1),
        None,
    )
    for entry in document["capacity_sweep"]:
        value = entry.get("engine_ms")
        if base and value:
            entry["speedup_vs_slots_1"] = round(base / value, 3)

    # -- project sweep ----------------------------------------------------
    for count in PROJECT_COUNTS:
        record, run_info = spawn(
            ["_projects", "--count", str(count),
             "--deadline", f"{time.time() + PROJECT_BUDGET_S:.3f}"],
            f"projects-{count}",
            PROJECT_BUDGET_S + 90.0,
        )
        record = record or {"projects": count, "status": run_info["status"],
                            "error": run_info["error"]}
        record["unit_run"] = run_info
        document["project_sweep"].append(record)
        document["runs"].append({"unit": "projects", **run_info})
        atomic_write(matrix_path, document)

    document["finished_at"] = datetime.now(timezone.utc).isoformat()
    document["matrix_phase_s"] = round(time.monotonic() - matrix_start, 1)
    document["status"] = "COMPLETE"
    atomic_write(matrix_path, document)

    # -- worker end to end ------------------------------------------------
    worker_doc: dict = {
        "schema": SCHEMA_WORKER,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git": git_information(),
        "environment": fingerprint,
        "postgres_version": document["postgres_version"],
        "dsn": dsn,
        "engine_under_test": "SchedulingEngineJobRunner via SchedulingWorkerRuntime over PostgreSQL",
        "seeding": "tests/integration/test_p0n2_runtime_activation.py::_seed_ready_scope/_seed_snapshot (copied minimal calls)",
        "submission": "SchedulingJobAPI.submit -> SchedulingJobService.submit (state QUEUED)",
        "retrieval": "SchedulingJobService.get/get_result after SchedulingWorkerRuntime.drain",
        "drain_timeout_s": WORKER_DRAIN_TIMEOUT_S,
        "runs": [],
        "status": "RUNNING",
    }
    atomic_write(worker_path, worker_doc)
    for size in WORKER_SIZES:
        for mode in WORKER_MODES:
            record, run_info = spawn(
                ["_worker", "--dsn", dsn, "--size", str(size), "--mode", mode,
                 "--deadline", f"{time.time() + WORKER_BUDGET_S:.3f}"],
                f"worker-{size}-{mode}",
                WORKER_BUDGET_S + 60.0,
            )
            record = record or {"size": size, "execution_mode": mode,
                                "status": run_info["status"], "error": run_info["error"]}
            record["unit_run"] = run_info
            worker_doc["runs"].append(record)
            atomic_write(worker_path, worker_doc)
    worker_doc["status"] = "COMPLETE"
    worker_doc["finished_at"] = datetime.now(timezone.utc).isoformat()
    atomic_write(worker_path, worker_doc)

    try:
        scratch.rmdir()
    except OSError:
        pass
    log.write(
        f"\nrun finished {datetime.now(timezone.utc).isoformat()}\n"
        f"matrix: {matrix_path}\nworker: {worker_path}\n"
    )
    print(json.dumps({
        "matrix": str(matrix_path),
        "worker": str(worker_path),
        "log": str(log_path),
        "cells": len(document["matrix_cells"]),
        "matrix_phase_s": document["matrix_phase_s"],
    }))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="p0n2_runtime_matrix.py")
    sub = parser.add_subparsers(dest="unit", required=True)

    run = sub.add_parser("run", help="orchestrate the whole evidence run")
    run.add_argument("--out-dir", required=True)
    run.add_argument("--dsn", default=DEFAULT_DSN)

    for name, help_text in (
        ("_cell", "one matrix cell"),
        ("_capacity", "one capacity-sweep point"),
        ("_projects", "one project-sweep scenario"),
        ("_worker", "one worker end-to-end run"),
    ):
        child = sub.add_parser(name, help=help_text)
        child.add_argument("--result-file", required=True)
        child.add_argument("--deadline", type=float, required=True)
        if name in ("_cell",):
            child.add_argument("--size", type=int, required=True)
            child.add_argument("--shape", required=True, choices=SHAPES)
            child.add_argument("--mode-budget", type=float, default=None,
                               help="override the per-mode budget for this cell")
        if name == "_capacity":
            child.add_argument("--slots", type=int, required=True)
        if name == "_projects":
            child.add_argument("--count", type=int, required=True)
        if name == "_worker":
            child.add_argument("--dsn", required=True)
            child.add_argument("--size", type=int, required=True)
            child.add_argument("--mode", required=True, choices=WORKER_MODES)

    report = sub.add_parser("report", help="render the markdown from the raw JSON")
    report.add_argument("--matrix", required=True)
    report.add_argument("--worker", required=True)
    report.add_argument("--md", required=True)

    arguments = parser.parse_args(argv)
    if arguments.unit == "run":
        return orchestrate(arguments)
    if arguments.unit == "report":
        return render_report(arguments)
    return child_main(arguments)


# ---------------------------------------------------------------------------
# Markdown report: every number is read back from the raw JSON
# ---------------------------------------------------------------------------


def ms(value) -> str:
    return "n/a" if value is None else f"{value:,.1f}"


def seconds(value) -> str:
    return "n/a" if value is None else f"{value:,.3f}"


def short(hash_value) -> str:
    return "n/a" if not hash_value else hash_value[:16]


def render_report(arguments: argparse.Namespace) -> int:
    matrix = json.loads(Path(arguments.matrix).read_text(encoding="utf-8"))
    worker = json.loads(Path(arguments.worker).read_text(encoding="utf-8"))
    definitions = matrix["definitions"]
    lines: list[str] = []
    add = lines.append

    environment = matrix["environment"]
    add("# P0-N.2 performance and capacity evidence")
    add("")
    add(f"Generated from the raw JSON of a single instrumented run: "
        f"`{Path(arguments.matrix).name}` and `{Path(arguments.worker).name}`. "
        "Every number in every table below is read back from those files; nothing is "
        "estimated, extrapolated or copied from an earlier run. Cells that did not "
        "complete are listed with their exact recorded error text.")
    add("")
    add("## Environment")
    add("")
    add("| Item | Value |")
    add("| --- | --- |")
    for key in ("python", "platform", "machine", "cpu_count", "cpu_affinity_count",
                "memory_total_kb", "git_sha"):
        add(f"| {key} | {environment.get(key)} |")
    add(f"| branch | {matrix['git'].get('branch')} |")
    add(f"| commit | {matrix['git'].get('commit')} |")
    add(f"| PostgreSQL | {matrix.get('postgres_version')} |")
    add(f"| started | {matrix.get('started_at')} |")
    add(f"| finished | {matrix.get('finished_at')} |")
    add(f"| matrix phase wall clock | {matrix.get('matrix_phase_s')} s |")
    add("")
    add("Working tree at run time (`git status --porcelain`, pre-existing edits made by "
        "other work in this session, **not** by this harness — the harness only writes "
        "the evidence files listed in Scope):")
    add("")
    add("```")
    add(matrix["git"].get("working_tree_porcelain") or "(clean)")
    add("```")
    add("")
    add("## Exact commands")
    add("")
    add("```")
    add(" ".join(matrix["argv"]))
    add("```")
    add("")
    add("The orchestrator spawns one subprocess per unit; the recorded command lines "
        "(in `runs[].command` of the raw matrix JSON, in `runs[].unit_run.command` of the "
        "worker JSON, and prefixed with `$ ` in the `.log`) are:")
    add("")
    add("```")
    for run_info in matrix["runs"]:
        add(run_info.get("command", "(not spawned)"))
    for entry in worker.get("runs", []):
        add((entry.get("unit_run") or {}).get("command", "(worker command not recorded)"))
    add("```")
    add("")
    if matrix.get("post_phase_reruns"):
        add("## Post-phase re-runs")
        add("")
        add(matrix.get("post_phase_rerun_note") or "")
        add("")
        add("| size | shape | status | overriding command |")
        add("| --- | --- | --- | --- |")
        commands = {
            (cell.get("size"), cell.get("shape")): (cell.get("unit_run") or {}).get("command")
            for cell in matrix["matrix_cells"]
            if cell.get("post_phase_rerun")
        }
        for entry in matrix["post_phase_reruns"]:
            key = (entry.get("size"), entry.get("shape"))
            add(f"| {key[0]} | {key[1]} | {entry.get('status')} | "
                f"`{commands.get(key) or 'not recorded'}` |")
        add("")
        add("Superseded first-pass records, with their exact error text:")
        add("")
        for cell in matrix["matrix_cells"]:
            superseded = cell.get("superseded_record")
            if not superseded:
                continue
            add(f"- ({cell.get('size')}, {cell.get('shape')}) was "
                f"`{superseded.get('status')}`: {superseded.get('error')}")
        add("")
    add("## Fixture definitions")
    add("")
    add("| Shape | Definition (recorded) |")
    add("| --- | --- |")
    for shape in definitions["shapes"]:
        add(f"| {shape} | `{definitions['shape_definitions'][shape]}` |")
    add("")
    add(f"- seed: `{definitions['seed']}`; sizes: `{definitions['sizes']}`")
    add(f"- constraint targets: `{definitions['constraint_target_formula']}`")
    add(f"- project finish passed to the engine: `{definitions['project_finish_source']}`")
    add(f"- sequential mode: `{definitions['sequential']}`")
    add(f"- parallel mode: `{definitions['parallel']}`")
    add(f"- repeats: small sizes {definitions['repeats']['small_sizes']} -> "
        f"{definitions['repeats']['small']} (median reported), 25000+ -> "
        f"{definitions['repeats']['large']}")
    add(f"- timeout policy: {definitions['timeout_policy']}; per-mode budgets (s): "
        f"`{definitions['mode_budget_s']}`; matrix phase deadline "
        f"`{definitions['matrix_phase_deadline_s']}` s")
    add("")
    add("## Matrix: sequential vs parallel (slots=4) on the real engine")
    add("")
    add("| size | shape | activities | relationships | constraints | seq median ms | par ms | "
        "seq CPU s | par CPU s | hash equality |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for cell in matrix["matrix_cells"]:
        modes = cell.get("modes") or {}
        seq = modes.get("sequential") or {}
        par = modes.get("parallel") or {}
        equality = cell.get("hash_equality") or {}
        add(
            f"| {cell.get('size')} | {cell.get('shape')} | {cell.get('activities', 'n/a')} | "
            f"{cell.get('relationships', 'n/a')} | {cell.get('constraints', 'n/a')} | "
            f"{ms(seq.get('engine_ms_median'))} | {ms(par.get('engine_ms_median'))} | "
            f"{seconds(seq.get('cpu_seconds_total'))} | {seconds(par.get('cpu_seconds_total'))} | "
            f"{equality.get('status', 'NOT_EVALUABLE')} |"
        )
    add("")
    add("### Matrix hashes and per-mode status")
    add("")
    add("| size | shape | mode | status | engine ms (every run) | CPU s (every run) | hash | "
        "internal agreement | min total float h | max total float h |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for cell in matrix["matrix_cells"]:
        for mode in ("sequential", "parallel"):
            block = (cell.get("modes") or {}).get(mode)
            if block is None:
                add(f"| {cell.get('size')} | {cell.get('shape')} | {mode} | ABSENT | n/a | n/a "
                    "| n/a | n/a | n/a | n/a |")
                continue
            runs = block.get("runs") or []
            add(
                f"| {cell.get('size')} | {cell.get('shape')} | {mode} | {block.get('status')} | "
                f"{', '.join(str(run['engine_ms']) for run in runs) or 'n/a'} | "
                f"{', '.join(str(run['cpu_seconds']) for run in runs) or 'n/a'} | "
                f"{short(block.get('hash'))} | {block.get('internal_hash_agreement')} | "
                f"{', '.join(str(run.get('min_total_float_hours')) for run in runs) or 'n/a'} | "
                f"{', '.join(str(run.get('max_total_float_hours')) for run in runs) or 'n/a'} |"
            )
    add("")
    add("## Capacity sweep: 25000 mixed at slots 1/2/4/8/16")
    add("")
    add("| slots | float_workers | wall ms | CPU s | speedup vs slots=1 | hash | matches matrix cell |")
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for entry in matrix["capacity_sweep"]:
        add(
            f"| {entry.get('slots')} | {entry.get('float_workers', 'n/a')} | "
            f"{ms(entry.get('engine_ms'))} | {seconds(entry.get('cpu_seconds'))} | "
            f"{entry.get('speedup_vs_slots_1', 'n/a')} | {short(entry.get('hash'))} | "
            f"{entry.get('hash_equals_matrix_cell')} |"
        )
    add("")
    add(f"Status / error per point: " + "; ".join(
        f"slots={entry.get('slots')}: {entry.get('status')}"
        + (f" ({entry.get('error')})" if entry.get("error") else "")
        for entry in matrix["capacity_sweep"]
    ))
    add("")
    add("## Project sweep: N concurrent 5000-activity projects, GlobalExecutionBudget(4)")
    add("")
    add("| projects | wall ms | throughput proj/s | peak slots | process starts | queue wait max ms | all hashes match | status |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for entry in matrix["project_sweep"]:
        add(
            f"| {entry.get('projects')} | {ms(entry.get('wall_ms'))} | "
            f"{entry.get('throughput_projects_per_s')} | {entry.get('peak_slots')} | "
            f"{entry.get('process_starts')} | {entry.get('queue_wait_ms_max')} | "
            f"{entry.get('hashes_match')} | {entry.get('status')}"
            + (f" — `{entry.get('error')}`" if entry.get("error") else "") + " |"
        )
    add("")
    add("### Per-project hashes (scheduled vs that project's own sequential run)")
    add("")
    add("| projects | seed | tenant | state | slots | run ms | queue wait ms | sequential hash | scheduled hash | match |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for entry in matrix["project_sweep"]:
        for job in entry.get("jobs") or []:
            add(
                f"| {entry.get('projects')} | {job.get('seed')} | {job.get('tenant')} | "
                f"{job.get('state')} | {job.get('slots')} | {job.get('run_ms')} | "
                f"{job.get('queue_wait_ms')} | {short(job.get('sequential_hash'))} | "
                f"{short(job.get('scheduled_hash'))} | {job.get('hash_match')} |"
            )
    add("")
    add("## Worker end to end: real PostgreSQL + real SchedulingWorkerRuntime")
    add("")
    add("| size | mode | state | attempts | submit ms | drain ms | e2e ms | DB submit->SUCCEEDED ms | output_hash == calculation_run_identity |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for entry in worker["runs"]:
        add(
            f"| {entry.get('size')} | {entry.get('execution_mode')} | {entry.get('state', 'n/a')} | "
            f"{entry.get('attempts', 'n/a')} | {entry.get('submit_ms', 'n/a')} | "
            f"{entry.get('drain_ms', 'n/a')} | {entry.get('e2e_ms', 'n/a')} | "
            f"{entry.get('db_submit_to_succeeded_ms', 'n/a')} | {entry.get('hash_match')} |"
        )
    add("")
    add("### Worker run detail")
    add("")
    for entry in worker["runs"]:
        add(f"- size={entry.get('size')} mode={entry.get('execution_mode')}: "
            f"job_id `{entry.get('job_id')}`, tenant `{entry.get('tenant_id')}`, "
            f"snapshot `{entry.get('snapshot_id')}`, state `{entry.get('state')}`, "
            f"attempts `{entry.get('attempts')}`, lease owner `{entry.get('lease_owner')}`, "
            f"activity_count `{entry.get('result_activity_count')}`, "
            f"output_hash `{entry.get('output_hash')}`, "
            f"calculation_run_identity `{entry.get('calculation_run_identity')}`, "
            f"match `{entry.get('hash_match')}`, status `{entry.get('status')}`"
            + (f", error `{entry.get('error')}`" if entry.get("error") else ""))
        add(f"  - settings: `{json.dumps(entry.get('worker_settings'))}`, "
            f"outcome: `{json.dumps(entry.get('outcome'), default=str)}`")
    add("")
    add("## Integrity notes")
    add("")
    for note in definitions.get("notes") or []:
        add(f"- {note}")
    add("")
    add(f"- Engine actually called: `{definitions.get('engine_module')}`")
    add("")
    if matrix.get("note_corrections"):
        add("### Post-run note corrections")
        add("")
        add("A note written at run time became stale before publication; the original text is "
            "kept here so the edit is auditable rather than silent.")
        add("")
        for correction in matrix["note_corrections"]:
            add(f"- was: {correction.get('was')}")
            add(f"- is now: {correction.get('now')}")
        add("")
    add("## Recorded failures, timeouts and skipped cells")
    add("")
    problems = []
    for cell in matrix["matrix_cells"]:
        if cell.get("status") != "OK":
            problems.append(
                f"- cell size={cell.get('size')} shape={cell.get('shape')}: "
                f"`{cell.get('status')}` — `{cell.get('error')}`"
            )
        for mode, block in (cell.get("modes") or {}).items():
            if block.get("status") != "OK":
                problems.append(
                    f"- cell size={cell.get('size')} shape={cell.get('shape')} mode={mode}: "
                    f"`{block.get('status')}` — `{block.get('error')}` (budget "
                    f"{block.get('budget_s')} s)"
                )
        equality = cell.get("hash_equality") or {}
        if equality.get("status") not in ("PASS",):
            problems.append(
                f"- hash equality size={cell.get('size')} shape={cell.get('shape')}: "
                f"`{equality.get('status')}` — `{equality.get('error') or equality.get('reason')}`"
            )
    for entry in matrix["capacity_sweep"]:
        if entry.get("status") != "OK" or entry.get("hash_equals_matrix_cell") is not True:
            problems.append(f"- capacity slots={entry.get('slots')}: `{entry.get('status')}` — "
                             f"`{entry.get('error')}` (matrix hash match "
                             f"{entry.get('hash_equals_matrix_cell')})")
    for entry in matrix["project_sweep"]:
        if entry.get("status") != "OK" or entry.get("hashes_match") is not True:
            problems.append(f"- project sweep count={entry.get('projects')}: `{entry.get('status')}` — "
                            f"`{entry.get('error')}` (hashes_match {entry.get('hashes_match')})")
            for job in entry.get("jobs") or []:
                if job.get("state") != "SUCCEEDED" or job.get("hash_match") is not True:
                    problems.append(f"  - job {job.get('project')}: state `{job.get('state')}`, "
                                    f"match `{job.get('hash_match')}`, error `{job.get('error')}`")
    for entry in worker["runs"]:
        if entry.get("status") != "OK" or entry.get("hash_match") is not True:
            problems.append(f"- worker size={entry.get('size')} mode={entry.get('execution_mode')}: "
                            f"`{entry.get('status')}` — `{entry.get('error')}`")
    if problems:
        lines.extend(problems)
    else:
        add("- none: every recorded cell, sweep point, project and worker run completed and matched.")
    add("")
    add("## Scope note")
    add("")
    add("This document and the harness are measurement only. No product code, test, "
        "configuration or committed artifact outside `docs/workspace/evidence/"
        "p0n-runtime-activation-2026-11-20/` was changed, and nothing was deleted from "
        "the shared PostgreSQL tables: each worker run seeds its own unique tenant scope, "
        "exactly like the integration test it mirrors.")
    add("")
    Path(arguments.md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"md": str(arguments.md), "lines": len(lines), "problems": len(problems)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
