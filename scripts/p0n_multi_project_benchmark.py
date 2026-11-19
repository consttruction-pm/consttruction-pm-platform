#!/usr/bin/env python3
"""P0-N: multi-project orchestration benchmark on the real engine.

Every number comes from a real call to the authoritative time-aware engine on
this machine. Nothing is extrapolated: a scenario that cannot finish inside its
timeout is recorded as an error, and a missing measurement is reported as
``null`` rather than estimated.

What is measured
----------------
* Scenario A-H of the P0-N mission: 1/2/4/8/10 large projects, 10 large + 5
  small, 10 large + 20 small, and 10 large projects with staggered arrivals.
* Per scenario: queue wait, start delay, compute time, total completion, CPU
  utilisation, peak RSS, active workers, cache hits/misses, process-start and
  IPC overhead, context switches, throughput and P50/P95/P99 of job time.
* Capacity sweep at 1/2/4/8/16/32 slots.
* Cold and warm result cache passes.
* Sequential and thread-pool baselines (the GIL reference).
* A repeated-run soak with RSS sampling for leak detection.

Execution model
---------------
``GlobalWorkerScheduler`` owns the one global budget. Each project is one
process holding its granted slots; inside that process the float pass may fork
at most ``slots - 1`` children, so the total number of OS processes never
exceeds the budget. The parent process only dispatches, samples and measures;
it never calculates.

Usage
-----
    python3 scripts/p0n_multi_project_benchmark.py --out /tmp/p0n.json
    python3 scripts/p0n_multi_project_benchmark.py --quick   # smoke run
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import pickle
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from functools import partial
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from construction_pm.scheduling.benchmark_fixtures import (  # noqa: E402
    TIME_PROJECT_START,
    canonical_hash,
    environment_fingerprint,
    time_calendar,
    time_network,
    time_schedule_payload,
)
from construction_pm.scheduling.calendar_context import (  # noqa: E402
    CalendarReference,
    CalendarResolverRegistry,
    SchedulingCalendarContext,
)
from construction_pm.scheduling.time_calendar import (  # noqa: E402
    TimeAwareWorkingTimeResolver,
    WorkingTimeCalendar,
)
from construction_pm.scheduling.time_constraints import (  # noqa: E402
    TimeActivityConstraint,
    TimeConstraintType,
)
from construction_pm.scheduling.time_forward_pass import TimeActivity  # noqa: E402
from construction_pm.scheduling.time_schedule import (  # noqa: E402
    FloatExecutionPolicy,
    time_schedule,
)
from construction_pm.scheduling_execution_budget import (  # noqa: E402
    GlobalExecutionBudget,
)
from construction_pm.scheduling_job_executor import SchedulingJobExecutor  # noqa: E402
from construction_pm.scheduling_job_lifecycle import (  # noqa: E402
    InMemorySchedulingJobRepository,
    SchedulingJobRequest,
    SchedulingJobResult,
    SchedulingJobService,
)
from construction_pm.scheduling_result_cache import CacheKey, ScheduleResultCache  # noqa: E402
from construction_pm.scheduling_worker_scheduler import (  # noqa: E402
    GlobalWorkerScheduler,
    ProjectWorkload,
    make_slot_admission,
)

SCHEMA = "construction-pm/p0n-multi-project-benchmark/v1"


# ---------------------------------------------------------------------------
# Project catalogue
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectSpec:
    name: str
    size: int
    shape: str
    seed: int
    tenant: str
    priority: int = 0
    variant: str = "standard"

    def workload(self) -> ProjectWorkload:
        relationships = _relationship_estimate(self.size, self.shape)
        return ProjectWorkload(self.size, relationships)


def _relationship_estimate(size: int, shape: str) -> int:
    if shape == "wide":
        return 0
    if shape == "chain":
        return max(0, size - 1)
    if shape in ("fan", "slack"):
        return max(0, 2 * size - 4)
    return max(0, size - 1 + (size - 1) * 2)


def _six_day_calendar() -> WorkingTimeCalendar:
    """A second project calendar: six days, 07:00-15:00."""
    from datetime import time as day_time

    interval = ((day_time(7), day_time(15)),)
    return WorkingTimeCalendar(
        holidays=frozenset(),
        daily_intervals={weekday: interval for weekday in range(6)},
    )


def _multi_calendar_fixture(spec: ProjectSpec):
    """Two calendars on one network plus real constraints.

    The base network is a standard DAG; every third activity moves to a
    six-day calendar, so the forward pass must interleave calendar lookups.
    Two start-no-earlier-than constraints are added on working days.
    """
    base = time_network(spec.size, "dag", spec.seed)
    registry = CalendarResolverRegistry(
        time_resolvers={
            "site@1": TimeAwareWorkingTimeResolver(time_calendar()),
            "sixday@1": TimeAwareWorkingTimeResolver(_six_day_calendar()),
        }
    )
    six_ctx = SchedulingCalendarContext(
        project=CalendarReference("site", "1", "working-time"),
        activity=CalendarReference("sixday", "1", "working-time"),
        relationship_lag=CalendarReference("site", "1", "working-time"),
    )
    activities = tuple(
        TimeActivity(
            activity.id,
            activity.duration,
            six_ctx if index % 3 == 0 else activity.calendar_context,
            activity.actual_start,
        )
        for index, activity in enumerate(base.activities)
    )
    constraints = tuple(
        TimeActivityConstraint(
            f"ACT-{index:06d}",
            TimeConstraintType.START_NO_EARLIER_THAN,
            TIME_PROJECT_START + timedelta(days=3),
        )
        for index in (5, 11)
    )
    return (
        activities,
        base.relationships,
        registry,
        TIME_PROJECT_START,
        None,
        constraints,
    )


def fixture_for(spec: ProjectSpec):
    """Return ``(activities, relationships, registry, start, finish, constraints)``."""
    if spec.variant == "multi-calendar-constraints":
        return _multi_calendar_fixture(spec)
    base = time_network(spec.size, spec.shape, spec.seed)
    return (
        base.activities,
        base.relationships,
        base.registry,
        base.project_start,
        base.project_finish,
        (),
    )


def run_project(spec: ProjectSpec, slots: int) -> dict[str, object]:
    """The unit of work handed to the scheduler (runs inside the job process).

    ``slots`` is the exact grant: the project may use ``slots - 1`` float
    children so that the project plus its children never exceed ``slots``.
    """
    cpu_started = os.times()
    activities, relationships, registry, start, finish, constraints = fixture_for(spec)
    workers = max(1, slots - 1)
    policy = FloatExecutionPolicy(
        workers=workers,
        admission=make_slot_admission(slots),
        allow_nested_fork=workers > 1,
    )
    started = time.perf_counter()
    result = time_schedule(
        activities,
        relationships,
        start,
        finish,
        registry,
        constraints,
        float_workers=workers,
        float_policy=policy,
    )
    elapsed = time.perf_counter() - started
    cpu_now = os.times()
    cpu_seconds = (
        (cpu_now.user + cpu_now.system + cpu_now.children_user + cpu_now.children_system)
        - (cpu_started.user + cpu_started.system + cpu_started.children_user + cpu_started.children_system)
    )
    payload = time_schedule_payload(result)
    return {
        "hash": canonical_hash(payload),
        "activities": len(activities),
        "relationships": len(relationships),
        "slots": slots,
        "float_workers": workers,
        "engine_ms": elapsed * 1000.0,
        "finish": result.project_finish.isoformat(),
        "cpu_seconds": max(0.0, float(cpu_seconds)),
    }


# ---------------------------------------------------------------------------
# Resource sampling
# ---------------------------------------------------------------------------


class ResourceSampler:
    """Sample the parent plus every live descendant, without threads.

    Started from the scheduler's ``tick`` callback, which runs on the dispatch
    loop before reaping, so a just-exited child still contributes its final
    CPU time and context-switch counters.
    """

    def __init__(self, interval: float = 0.1) -> None:
        self.proc = psutil.Process()
        self.interval = interval
        self.last = 0.0
        self.cpu_seconds = 0.0
        self.voluntary = 0
        self.involuntary = 0
        self.peak_rss_bytes = 0
        self.peak_workers = 0
        self.samples: list[dict[str, float]] = []
        self._last: dict[int, tuple[float, float, int, int]] = {}

    def reset(self) -> None:
        self.last = 0.0
        self.cpu_seconds = 0.0
        self.voluntary = 0
        self.involuntary = 0
        self.peak_rss_bytes = 0
        self.peak_workers = 0
        self.samples = []
        self._last = {}
        self.sample(force=True)

    def _tree(self):
        procs = [self.proc]
        try:
            procs.extend(self.proc.children(recursive=True))
        except psutil.Error:
            pass
        return procs

    def sample(self, *, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self.last < self.interval:
            return
        self.last = now
        total_rss = 0
        workers = 0
        for process in self._tree():
            try:
                pid = process.pid
                times = process.cpu_times()
                counters = process.num_ctx_switches()
                memory = process.memory_info().rss
            except psutil.Error:
                continue
            total_rss += memory
            if pid != self.proc.pid:
                workers += 1
            previous = self._last.get(pid)
            if previous is None:
                self._last[pid] = (
                    times.user,
                    times.system,
                    counters.voluntary,
                    counters.involuntary,
                )
                continue
            self.cpu_seconds += max(0.0, (times.user + times.system) - (previous[0] + previous[1]))
            self.voluntary += max(0, counters.voluntary - previous[2])
            self.involuntary += max(0, counters.involuntary - previous[3])
            self._last[pid] = (
                times.user,
                times.system,
                counters.voluntary,
                counters.involuntary,
            )
        self.peak_rss_bytes = max(self.peak_rss_bytes, total_rss)
        self.peak_workers = max(self.peak_workers, workers)
        self.samples.append({"t": now, "rss_bytes": total_rss, "workers": workers})

    def summary(self, wall_seconds: float, cores: int) -> dict[str, object]:
        cpu_pct = 0.0
        if wall_seconds > 0 and cores > 0:
            cpu_pct = 100.0 * self.cpu_seconds / (wall_seconds * cores)
        return {
            "cpu_seconds": round(self.cpu_seconds, 3),
            "cpu_cores_used": round(self.cpu_seconds / wall_seconds, 2) if wall_seconds else None,
            "cpu_utilization_pct": round(cpu_pct, 1),
            "peak_rss_mb": round(self.peak_rss_bytes / (1024 * 1024), 1),
            "peak_worker_processes": self.peak_workers,
            "context_switches_voluntary": self.voluntary,
            "context_switches_involuntary": self.involuntary,
            "samples": self.samples,
        }


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def latency_block(values: list[float]) -> dict[str, float | None]:
    return {
        "mean": round(statistics.fmean(values), 3) if values else None,
        "p50": round(percentile(values, 0.50), 3) if values else None,
        "p95": round(percentile(values, 0.95), 3) if values else None,
        "p99": round(percentile(values, 0.99), 3) if values else None,
        "max": round(max(values), 3) if values else None,
    }


def median(values: list[float]) -> float | None:
    return round(statistics.median(values), 3) if values else None


# ---------------------------------------------------------------------------
# Scenario execution
# ---------------------------------------------------------------------------


def _cache_key(spec: ProjectSpec, tag: str) -> CacheKey:
    return CacheKey(
        tenant_id=spec.tenant,
        project_id=spec.name,
        calculation_identity=f"p0n-{spec.name}-{tag}",
        engine_version="cubi-26.0.0",
    )


def run_scenario(
    specs: list[ProjectSpec],
    *,
    budget: int,
    tag: str,
    cache: ScheduleResultCache | None = None,
    delays: list[float] | None = None,
    expected_hashes: dict[str, str] | None = None,
    timeout: float = 900.0,
    sample_interval: float = 0.05,
    start_method: str | None = None,
) -> dict[str, object]:
    """Run every spec concurrently under one global budget and measure it."""
    sampler = ResourceSampler(sample_interval)
    scheduler = GlobalWorkerScheduler(
        budget=GlobalExecutionBudget(budget),
        poll_interval=0.005,
        tick=sampler.sample,
        start_method=start_method,
    )
    if cache is not None:
        scheduler.attach_result_cache(cache)
    sampler.reset()
    started = time.perf_counter()
    for index, spec in enumerate(specs):
        scheduler.submit(
            f"{tag}-{index:02d}-{spec.name}",
            partial(run_project, spec),
            workload=spec.workload(),
            priority=spec.priority,
            tenant_id=spec.tenant,
            cache_key=_cache_key(spec, tag) if cache is not None else None,
            release_at=None if delays is None else time.monotonic() + delays[index],
        )
    error: str | None = None
    try:
        scheduler.run_until_idle(timeout=timeout)
    except Exception as failure:  # noqa: BLE001 - reported, never hidden
        error = f"{type(failure).__name__}: {failure}"
    wall = time.perf_counter() - started
    sampler.sample(force=True)
    snapshot = scheduler.snapshot()
    rows = scheduler.results()
    jobs = []
    payload_bytes = 0
    hashes_ok = True
    for row in rows:
        value = scheduler.value_for(str(row["key"]))
        encoded = len(pickle.dumps(value)) if row["state"] in ("SUCCEEDED", "CACHE_HIT") else 0
        payload_bytes += encoded
        key = str(row["key"])
        spec = specs[int(key.rsplit("-", 2)[1])]
        actual = value.get("hash") if isinstance(value, dict) else None
        expected = None if expected_hashes is None else expected_hashes.get(spec.name)
        match = expected is None or actual == expected
        hashes_ok = hashes_ok and match
        jobs.append(
            {
                "key": key,
                "project": spec.name,
                "size": spec.size,
                "shape": spec.shape,
                "variant": spec.variant,
                "tenant": spec.tenant,
                "state": row["state"],
                "cache_hit": row["cache_hit"],
                "slots": row["slots"],
                "queue_wait_ms": None
                if row["queue_wait_ms"] is None
                else round(float(row["queue_wait_ms"]), 2),
                "run_ms": None if row["run_ms"] is None else round(float(row["run_ms"]), 2),
                "child_run_ms": None
                if row["child_run_ms"] is None
                else round(float(row["child_run_ms"]), 2),
                "overhead_ms": None
                if row["overhead_ms"] is None
                else round(float(row["overhead_ms"]), 2),
                "cpu_seconds": row["cpu_seconds"],
                "payload_bytes": encoded,
                "hash": actual,
                "hash_match": match,
                "error": row["error"],
            }
        )
    run_values = [float(job["run_ms"]) for job in jobs if job["run_ms"] is not None]
    wait_values = [float(job["queue_wait_ms"]) for job in jobs if job["queue_wait_ms"] is not None]
    overhead_values = [
        float(job["overhead_ms"]) for job in jobs if job["overhead_ms"] is not None
    ]
    start_values = [
        float(job["queue_wait_ms"]) + float(job["run_ms"])
        for job in jobs
        if job["queue_wait_ms"] is not None and job["run_ms"] is not None
    ]
    hits = sum(1 for job in jobs if job["cache_hit"])
    cores = psutil.cpu_count(logical=True) or 1
    resources = sampler.summary(wall, cores)
    job_cpu = sum(
        float(job["cpu_seconds"]) for job in jobs if job["cpu_seconds"] is not None
    )
    measured_utilization = (
        round(100.0 * job_cpu / (wall * cores), 1) if wall > 0 else None
    )
    return {
        "tag": tag,
        "projects": len(specs),
        "budget": budget,
        "wall_ms": round(wall * 1000.0, 1),
        "throughput_projects_per_s": round(len(specs) / wall, 3) if wall else None,
        "throughput_activities_per_s": round(
            sum(spec.size for spec in specs) / wall, 1
        )
        if wall
        else None,
        "queue_wait": latency_block(wait_values),
        "job_time": latency_block(run_values),
        "start_delay": latency_block(start_values),
        "ipc_overhead": latency_block(overhead_values),
        "cache": {
            "hits": hits,
            "misses": len(jobs) - hits,
            "hit_ratio": round(hits / len(jobs), 3) if jobs else None,
        },
        "payload_bytes_total": payload_bytes,
        "peak_slots": snapshot.get("peak_slots"),
        "slots_acquired_total": snapshot.get("slots_acquired_total"),
        "process_starts": snapshot.get("process_starts"),
        "inline_fallbacks": snapshot.get("inline_fallbacks"),
        "slots_held_after": snapshot.get("slots_held"),
        "budget_after": scheduler.budget.active,
        "hashes_match": hashes_ok,
        "error": error,
        "job_cpu_seconds": round(job_cpu, 3),
        "cpu_utilization_pct": measured_utilization,
        "resources": {k: v for k, v in resources.items() if k != "samples"},
        "jobs": jobs,
        "_samples": resources["samples"],
    }


def strip_series(result: dict[str, object]) -> dict[str, object]:
    clean = dict(result)
    clean.pop("_samples", None)
    return clean


# ---------------------------------------------------------------------------
# Durable executor end to end
# ---------------------------------------------------------------------------


def executor_scenario(
    specs: list[ProjectSpec], *, budget: int = 4, timeout: float = 300.0
) -> dict[str, object]:
    """The production job path: submissions, the executor loop, persistence.

    This is the same loop a worker runs. In process mode every job is placed in
    its own child that may use the granted slots for float children; the
    executor persists the returned hash through the lifecycle service.
    """
    by_project = {spec.name: spec for spec in specs}
    service = SchedulingJobService(
        InMemorySchedulingJobRepository(), lease_ttl=timedelta(seconds=120)
    )
    job_ids: dict[str, str] = {}
    for index, spec in enumerate(specs):
        submission = service.submit(
            SchedulingJobRequest(
                tenant_id=spec.tenant,
                project_id=spec.name,
                submitted_by="bench",
                request_fingerprint=f"fp-{index}",
                engine_version="cubi-26.0.0",
                calculation_identity=f"p0n-exec-{index}",
            )
        )
        job_ids[spec.name] = submission.job.job_id

    def calculate(job) -> SchedulingJobResult:
        return _result(job, 1)

    def calculate_with_slots(job, slots: int) -> SchedulingJobResult:
        return _result(job, slots)

    def _result(job, slots: int) -> SchedulingJobResult:
        value = run_project(by_project[job.project_id], slots)
        return SchedulingJobResult(
            tenant_id=job.tenant_id,
            project_id=job.project_id,
            job_id=job.job_id,
            engine_version=job.engine_version,
            calculation_identity=job.calculation_identity,
            output_hash=str(value["hash"]),
            payload=value,
            persisted_at=datetime.now(timezone.utc),
        )

    sampler = ResourceSampler()
    executor = SchedulingJobExecutor(
        service,
        calculate=calculate,
        owner="bench-worker",
        budget=GlobalExecutionBudget(budget),
        execution_mode="process",
        poll_interval=0.002,
        idle_polls_before_exit=3,
        workload_estimator=lambda job: by_project[job.project_id].workload(),
        calculate_with_slots=calculate_with_slots,
    )
    sampler.reset()
    started = time.perf_counter()
    summary = executor.run_until_idle(timeout=timeout)
    wall = time.perf_counter() - started
    sampler.sample(force=True)
    cores = psutil.cpu_count(logical=True) or 1
    persisted: dict[str, str] = {}
    for spec in specs:
        result = service.get_result(
            tenant_id=spec.tenant,
            project_id=spec.name,
            job_id=job_ids[spec.name],
            user_id="bench",
        )
        persisted[spec.name] = result.output_hash
    return {
        "engine": "SchedulingJobExecutor, execution_mode=process, in-memory adapter",
        "projects": len(specs),
        "budget": budget,
        "wall_ms": round(wall * 1000.0, 1),
        "throughput_projects_per_s": round(len(specs) / wall, 3),
        "cpu_utilization_pct": round(
            100.0 * _job_cpu_total(service, job_ids, specs) / (wall * cores), 1
        )
        if wall
        else None,
        "summary": summary.as_dict(),
        "persisted_hashes": persisted,
        "resources": {
            key: value
            for key, value in sampler.summary(wall, cores).items()
            if key != "samples"
        },
    }


def _job_cpu_total(service, job_ids, specs) -> float:
    total = 0.0
    for spec in specs:
        result = service.get_result(
            tenant_id=spec.tenant,
            project_id=spec.name,
            job_id=job_ids[spec.name],
            user_id="bench",
        )
        value = result.payload.get("cpu_seconds")
        if value is None:
            value = result.payload.get("engine_ms", 0.0) / 1000.0
        total += float(value)
    return total


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------


def sequential_baseline(specs: list[ProjectSpec]) -> dict[str, object]:
    started = time.perf_counter()
    cpu_started = time.process_time()
    rows = []
    for spec in specs:
        begin = time.perf_counter()
        value = run_project(spec, 1)
        rows.append(
            {
                "project": spec.name,
                "size": spec.size,
                "wall_ms": round((time.perf_counter() - begin) * 1000.0, 1),
                "hash": value["hash"],
            }
        )
    wall = time.perf_counter() - started
    cpu = time.process_time() - cpu_started
    cores = psutil.cpu_count(logical=True) or 1
    return {
        "engine": "sequential float pass, one project at a time",
        "wall_ms": round(wall * 1000.0, 1),
        "throughput_projects_per_s": round(len(specs) / wall, 3),
        "cpu_seconds": round(cpu, 3),
        "cpu_utilization_pct": round(100.0 * cpu / (wall * cores), 1),
        "jobs": rows,
    }


def thread_pool_baseline(
    specs: list[ProjectSpec], *, workers: int = 4, float_workers: int = 4
) -> dict[str, object]:
    """The pre-P0-N shape: several projects as threads in one process.

    Each thread asks the engine for ``float_workers`` float workers, but a
    thread cannot fork, so the float pass runs sequentially and the GIL serial
    the CPU work. This is the reference the process placement must beat.
    """

    def compute(spec: ProjectSpec) -> dict[str, object]:
        activities, relationships, registry, start, finish, constraints = fixture_for(spec)
        policy = FloatExecutionPolicy(workers=float_workers)
        started = time.perf_counter()
        result = time_schedule(
            activities,
            relationships,
            start,
            finish,
            registry,
            constraints,
            float_workers=float_workers,
            float_policy=policy,
        )
        return {
            "wall_ms": round((time.perf_counter() - started) * 1000.0, 1),
            "hash": canonical_hash(time_schedule_payload(result)),
        }

    sampler = ResourceSampler()
    sampler.reset()
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(compute, specs))
    wall = time.perf_counter() - started
    sampler.sample(force=True)
    return {
        "engine": f"{workers} threads, float_workers={float_workers}",
        "wall_ms": round(wall * 1000.0, 1),
        "throughput_projects_per_s": round(len(specs) / wall, 3),
        "cpu_utilization_pct": sampler.summary(wall, psutil.cpu_count(logical=True) or 1)[
            "cpu_utilization_pct"
        ],
        "cpu_seconds": round(sampler.cpu_seconds, 3),
        "jobs": rows,
    }


# ---------------------------------------------------------------------------
# Programme
# ---------------------------------------------------------------------------


def git_sha() -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def large_catalogue(scale: str) -> list[ProjectSpec]:
    if scale == "quick":
        return [
            ProjectSpec("L1", 1200, "dag", 101, "tenant-a"),
            ProjectSpec("L2", 1000, "wide", 102, "tenant-b"),
            ProjectSpec("L3", 1100, "mixed", 103, "tenant-a"),
        ]
    return [
        ProjectSpec("L01", 5000, "dag", 101, "tenant-a"),
        ProjectSpec("L02", 4500, "wide", 102, "tenant-b"),
        ProjectSpec("L03", 5200, "fan", 103, "tenant-c"),
        ProjectSpec("L04", 4800, "mixed", 104, "tenant-a"),
        ProjectSpec("L05", 6000, "dag", 105, "tenant-b"),
        ProjectSpec("L06", 4200, "wide", 106, "tenant-d"),
        ProjectSpec("L07", 5500, "mixed", 107, "tenant-c"),
        ProjectSpec("L08", 4700, "fan", 108, "tenant-b"),
        ProjectSpec("L09", 5300, "mixed", 109, "tenant-a"),
        ProjectSpec(
            "L10", 4900, "dag", 110, "tenant-d", variant="multi-calendar-constraints"
        ),
    ]


def small_catalogue(count: int, scale: str) -> list[ProjectSpec]:
    shapes = ("dag", "wide", "mixed", "fan")
    base = 400 if scale == "quick" else 900
    return [
        ProjectSpec(
            f"S{index:02d}",
            base - (index % 5) * 40,
            shapes[index % len(shapes)],
            900 + index,
            f"tenant-{'abcd'[index % 4]}",
            priority=5,
        )
        for index in range(count)
    ]


def scenario_matrix(large: list[ProjectSpec], small: list[ProjectSpec]) -> dict[str, dict]:
    """Scenarios A-H of the mission, expressed as data."""
    five = small[:5]
    twenty = small[:20]
    staggered = [0.0, 0.0, 0.0, 0.0, 0.0] + [0.4 * (index + 1) for index in range(5)]
    return {
        "A_one_large": {"specs": large[:1], "delays": None},
        "B_two_large": {"specs": large[:2], "delays": None},
        "C_four_large": {"specs": large[:4], "delays": None},
        "D_eight_large": {"specs": large[:8], "delays": None},
        "E_ten_large": {"specs": large[:10], "delays": None},
        "F_ten_large_five_small": {"specs": large[:10] + five, "delays": None},
        "G_ten_large_twenty_small": {"specs": large[:10] + twenty, "delays": None},
        "H_ten_large_staggered": {
            "specs": large[:10],
            "delays": staggered[: len(large[:10])],
        },
    }


def aggregate_repeats(results: list[dict[str, object]]) -> dict[str, object]:
    walls = [float(result["wall_ms"]) for result in results]
    p95 = [float(result["job_time"]["p95"]) for result in results if result["job_time"]["p95"]]
    waits = [
        float(result["queue_wait"]["p95"])
        for result in results
        if result["queue_wait"]["p95"] is not None
    ]
    cpu = [float(result["cpu_utilization_pct"]) for result in results]
    return {
        "repeats": len(results),
        "wall_ms_median": median(walls),
        "wall_ms_min": round(min(walls), 1) if walls else None,
        "wall_ms_max": round(max(walls), 1) if walls else None,
        "throughput_projects_per_s_median": median(
            [float(result["throughput_projects_per_s"]) for result in results]
        ),
        "p95_job_ms_median": median(p95),
        "p95_queue_wait_ms_median": median(waits),
        "cpu_utilization_pct_median": median(cpu),
        "peak_rss_mb_max": max(float(result["resources"]["peak_rss_mb"]) for result in results),
        "peak_slots_max": max(int(result["peak_slots"]) for result in results),
        "hashes_all_match": all(bool(result["hashes_match"]) for result in results),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P0-N multi-project benchmark")
    parser.add_argument("--out", type=Path, default=Path("/tmp/p0n-benchmark.json"))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--budget", type=int, default=4)
    parser.add_argument("--scale", choices=("quick", "full"), default="full")
    parser.add_argument("--only", type=str, default="", help="comma separated scenario keys")
    parser.add_argument("--skip-sweep", action="store_true")
    parser.add_argument("--skip-soak", action="store_true")
    parser.add_argument("--skip-baselines", action="store_true")
    parser.add_argument("--skip-executor", action="store_true")
    parser.add_argument("--soak-iterations", type=int, default=8)
    parser.add_argument("--start-method", type=str, default=None)
    parser.add_argument("--quick", action="store_true", help="alias for --scale quick")
    args = parser.parse_args(argv)
    scale = "quick" if args.quick else args.scale

    large = large_catalogue(scale)
    small = small_catalogue(20, scale)
    scenarios = scenario_matrix(large, small)
    if args.only:
        wanted = {item.strip() for item in args.only.split(",") if item.strip()}
        scenarios = {key: value for key, value in scenarios.items() if key in wanted}

    expected: dict[str, str] = {}
    sequential: dict[str, object] | None = None
    if not args.skip_baselines:
        print("== sequential baseline ==", flush=True)
        baseline_specs = list({spec.name: spec for spec in large + small}.values())
        sequential = sequential_baseline(baseline_specs)
        for row in sequential["jobs"]:
            expected[row["project"]] = row["hash"]
        print(
            f"   {len(baseline_specs)} projects in {sequential['wall_ms'] / 1000:.1f}s",
            flush=True,
        )

    report: dict[str, object] = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha(),
        "scale": scale,
        "environment": environment_fingerprint(git_sha()),
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "start_method": args.start_method
        or ("fork" if "fork" in multiprocessing.get_all_start_methods() else "forkserver"),
        "catalogue": {
            "large": [asdict(spec) for spec in large],
            "small": [asdict(spec) for spec in small],
        },
        "sequential": strip_series(sequential) if sequential else None,
        "scenarios": {},
    }

    print("== scenarios ==", flush=True)
    for name, definition in scenarios.items():
        repeats = []
        for repeat in range(args.repeats):
            result = run_scenario(
                definition["specs"],
                budget=args.budget,
                tag=f"{name}-r{repeat}",
                delays=definition["delays"],
                expected_hashes=expected or None,
                start_method=args.start_method,
            )
            result["repeat"] = repeat
            repeats.append(result)
            print(
                f"   {name} r{repeat}: {result['wall_ms']:.0f}ms "
                f"cpu={result['resources']['cpu_utilization_pct']}% "
                f"p95={result['job_time']['p95']}ms "
                f"hash={'ok' if result['hashes_match'] else 'MISMATCH'}"
                f"{' error=' + result['error'] if result['error'] else ''}",
                flush=True,
            )
        report["scenarios"][name] = {
            "projects": len(definition["specs"]),
            "budget": args.budget,
            "staggered": definition["delays"] is not None,
            "repeats": [strip_series(result) for result in repeats],
            "aggregate": aggregate_repeats(repeats),
        }

    if not args.skip_sweep:
        print("== capacity sweep (scenario E) ==", flush=True)
        sweep = {}
        for budget in (1, 2, 4, 8, 16, 32):
            result = run_scenario(
                large[:10],
                budget=budget,
                tag=f"sweep-{budget}",
                expected_hashes=expected or None,
                start_method=args.start_method,
            )
            sweep[str(budget)] = strip_series(result)
            print(
                f"   budget={budget}: {result['wall_ms']:.0f}ms "
                f"peak_slots={result['peak_slots']} "
                f"cpu={result['resources']['cpu_utilization_pct']}% "
                f"hashes={'ok' if result['hashes_match'] else 'MISMATCH'}",
                flush=True,
            )
        report["capacity_sweep"] = sweep

    if not args.skip_executor:
        print("== durable executor end to end (4 large + 4 small) ==", flush=True)
        report["executor_end_to_end"] = executor_scenario(
            large[:4] + small[:4], budget=args.budget
        )
        end = report["executor_end_to_end"]
        executor_hashes_ok = all(
            expected.get(name, digest) == digest
            for name, digest in end["persisted_hashes"].items()
        ) if expected else True
        print(
            f"   wall={end['wall_ms']:.0f}ms cpu={end['cpu_utilization_pct']}% "
            f"process_starts={end['summary']['process_starts']} "
            f"peak_slots={end['summary']['peak_slots']} "
            f"hash={'ok' if executor_hashes_ok else 'MISMATCH'}",
            flush=True,
        )

    if not args.skip_baselines:
        print("== thread-pool baseline (scenario C) ==", flush=True)
        report["thread_pool_baseline"] = thread_pool_baseline(
            large[: int(args.budget)]
        )
        print(
            f"   threads {report['thread_pool_baseline']['wall_ms']:.0f}ms "
            f"cpu={report['thread_pool_baseline']['cpu_utilization_pct']}%",
            flush=True,
        )

    print("== cache cold/warm (scenario E) ==", flush=True)
    cache = ScheduleResultCache(max_weight_bytes=512 * 1024 * 1024)
    cold = run_scenario(
        large[:10],
        budget=args.budget,
        tag="cache-cold",
        cache=cache,
        expected_hashes=expected or None,
        start_method=args.start_method,
    )
    warm = run_scenario(
        large[:10],
        budget=args.budget,
        tag="cache-cold",
        cache=cache,
        expected_hashes=expected or None,
        start_method=args.start_method,
    )
    report["cache"] = {
        "cold": strip_series(cold),
        "warm": strip_series(warm),
        "stats": cache.stats(),
        "capacity_bytes": cache.capacity_bytes,
    }
    print(
        f"   cold={cold['wall_ms']:.0f}ms hits={cold['cache']['hits']} | "
        f"warm={warm['wall_ms']:.0f}ms hits={warm['cache']['hits']} "
        f"hash={'ok' if warm['hashes_match'] else 'MISMATCH'}",
        flush=True,
    )

    if not args.skip_soak:
        print("== repeated-run soak ==", flush=True)
        scheduler = GlobalWorkerScheduler(
            budget=GlobalExecutionBudget(args.budget),
            poll_interval=0.005,
            start_method=args.start_method,
        )
        iterations = args.soak_iterations
        rss_by_iteration: list[int] = []
        started = time.perf_counter()
        processor = psutil.Process()
        for iteration in range(iterations):
            for index, spec in enumerate(large[:2]):
                scheduler.submit(
                    f"soak-{iteration}-{index}",
                    partial(run_project, spec),
                    workload=spec.workload(),
                    tenant_id=spec.tenant,
                )
            scheduler.run_until_idle(timeout=600)
            snapshot = scheduler.snapshot()
            rss_by_iteration.append(processor.memory_info().rss)
            print(
                f"   iteration {iteration + 1}/{iterations}: "
                f"parent_rss={rss_by_iteration[-1] / (1024 * 1024):.1f}MB "
                f"slots_held={snapshot['slots_held']}",
                flush=True,
            )
        soak_wall = time.perf_counter() - started
        report["soak"] = {
            "iterations": iterations,
            "projects_per_iteration": 2,
            "wall_ms": round(soak_wall * 1000.0, 1),
            "rss_mb": [round(value / (1024 * 1024), 1) for value in rss_by_iteration],
            "rss_growth_mb": round(
                (rss_by_iteration[-1] - rss_by_iteration[0]) / (1024 * 1024), 1
            ),
            "slots_held_after": scheduler.budget.active,
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")
    print(f"\nwritten {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
