#!/usr/bin/env python3
"""P0-G worker benchmark: real throughput, latency and canonical equality.

Every worker is a real OS process that claims jobs from PostgreSQL, runs the
authoritative engine on the same immutable fixture and persists the canonical
hash through the P0-F lifecycle. The parent only submits and measures; it never
calculates.

    P6_TEST_POSTGRES_DSN=postgresql://... \
      python3 scripts/scheduling_worker_benchmark.py \
        --workers 1,2,4 --jobs 32 --size 200 --out /tmp/p0g.json

A requested worker count above the host's effective capacity is refused unless
``--allow-oversubscription`` is passed, in which case the run is recorded as
oversubscribed instead of being presented as scale proof.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import queue as queue_module
import resource
import statistics
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from construction_pm.postgres_scheduling_job_lifecycle import (  # noqa: E402
    PostgresSchedulingJobRepository,
)
from construction_pm.scheduling.benchmark_fixtures import (  # noqa: E402
    canonical_hash,
    date_network,
    date_schedule_payload,
    environment_fingerprint,
    run_date_schedule,
)
from construction_pm.scheduling_execution_budget import (  # noqa: E402
    GlobalExecutionBudget,
    WorkerBudgetPolicy,
    detect_effective_capacity,
)
from construction_pm.scheduling_job_executor import (  # noqa: E402
    SchedulingJobExecutor,
)
from construction_pm.scheduling_job_lifecycle import (  # noqa: E402
    SchedulingJobRequest,
    SchedulingJobResult,
    SchedulingJobService,
    SchedulingJobState,
)

ENGINE = "cubi-26.0.0"
CALCULATION = "p0g-worker-benchmark"


# ---------------------------------------------------------------------------
# Worker process
# ---------------------------------------------------------------------------


def _worker_main(config: dict, queue) -> None:  # pragma: no cover - subprocess
    import psycopg

    connection = psycopg.connect(config["dsn"], autocommit=True)
    repository = PostgresSchedulingJobRepository(connection)
    repository.initialize()
    service = SchedulingJobService(
        repository, lease_ttl=timedelta(seconds=config["lease_ttl"])
    )
    fixture = date_network(config["size"], "dag", config["seed"])
    owner = f"p0g-{os.getpid()}"
    budget = GlobalExecutionBudget(config["budget_per_process"])

    def calculate(job) -> SchedulingJobResult:
        result = run_date_schedule(fixture)
        return SchedulingJobResult(
            tenant_id=job.tenant_id,
            project_id=job.project_id,
            job_id=job.job_id,
            engine_version=job.engine_version,
            calculation_identity=job.calculation_identity,
            output_hash=canonical_hash(date_schedule_payload(result)),
            payload={"activities": len(fixture.activities)},
            persisted_at=datetime.now(timezone.utc),
        )

    def sink(event) -> None:
        queue.put(
            {
                "kind": event.kind,
                "job_id": event.job_id,
                "owner": event.owner,
                "at": event.at.timestamp(),
                "queue_wait_ms": event.queue_wait_ms,
                "run_ms": event.run_ms,
                "error": event.error,
            }
        )

    cpu_start = time.process_time()
    wall_start = time.perf_counter()
    executor = SchedulingJobExecutor(
        service,
        calculate=calculate,
        owner=owner,
        budget=budget,
        engine_identity=(ENGINE, CALCULATION),
        poll_interval=0.002,
        event_sink=sink,
    )
    summary = executor.run_until_idle(timeout=config["timeout"])
    queue.put(
        {
            "kind": "SUMMARY",
            "owner": owner,
            "summary": summary.as_dict(),
            "cpu_s": time.process_time() - cpu_start,
            "wall_s": time.perf_counter() - wall_start,
            "peak_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        }
    )
    connection.close()


# ---------------------------------------------------------------------------
# Parent
# ---------------------------------------------------------------------------


def _percentile(samples: list[float], fraction: float) -> float | None:
    if not samples:
        return None
    ordered = sorted(samples)
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return round(ordered[index], 3)


def _summary(values: list[float]) -> dict[str, object]:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "min": round(min(values), 3),
        "median": round(statistics.median(values), 3),
        "p50": _percentile(values, 0.50),
        "p95": _percentile(values, 0.95),
        "p99": _percentile(values, 0.99),
        "max": round(max(values), 3),
        "mean": round(statistics.fmean(values), 3),
    }


def _cleanup(connection, tenant: str) -> None:
    connection.execute("DELETE FROM scheduling_job_results WHERE tenant_id=%s", (tenant,))
    connection.execute("DELETE FROM scheduling_jobs WHERE tenant_id=%s", (tenant,))


def _run(args, workers: int, capacity, policy_budget) -> dict[str, object]:
    import psycopg

    tenant = f"p0g-bench-{uuid.uuid4()}"
    dsn = args.dsn
    setup = psycopg.connect(dsn, autocommit=True)
    try:
        repository = PostgresSchedulingJobRepository(setup)
        repository.initialize()
        _cleanup(setup, tenant)
        service = SchedulingJobService(
            repository, lease_ttl=timedelta(seconds=max(60.0, args.timeout))
        )
        submitted_at: dict[str, float] = {}
        for index in range(args.jobs):
            submission = service.submit(
                SchedulingJobRequest(
                    tenant_id=tenant,
                    project_id="project-bench",
                    submitted_by="alice",
                    request_fingerprint=f"job-{index:04d}",
                    engine_version=ENGINE,
                    calculation_identity=CALCULATION,
                    max_attempts=2,
                )
            )
            submitted_at[submission.job.job_id] = time.time()
    finally:
        setup.close()

    context = multiprocessing.get_context("fork")
    queue = context.Queue()
    config = {
        "dsn": dsn,
        "size": args.size,
        "seed": args.seed,
        "timeout": args.timeout,
        "lease_ttl": max(60.0, args.timeout),
        "budget_per_process": 1,
    }
    processes = [
        context.Process(target=_worker_main, args=(config, queue))
        for _ in range(workers)
    ]

    wall_start = time.perf_counter()
    for process in processes:
        process.start()
    for process in processes:
        process.join(args.timeout)
    wall = time.perf_counter() - wall_start

    events: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []
    while True:
        try:
            record = queue.get(timeout=0.5)
        except queue_module.Empty:
            break
        if record.get("kind") == "SUMMARY":
            summaries.append(record)
        else:
            events.append(record)

    queue_wait = [
        float(event["queue_wait_ms"])
        for event in events
        if event["kind"] == "CLAIMED" and event.get("queue_wait_ms") is not None
    ]
    latency = [
        (float(event["at"]) - submitted_at[str(event["job_id"])]) * 1000.0
        for event in events
        if event["kind"] == "SUCCEEDED" and str(event["job_id"]) in submitted_at
    ]
    run_ms = [
        float(event["run_ms"])
        for event in events
        if event["kind"] == "SUCCEEDED" and event.get("run_ms") is not None
    ]

    verify = psycopg.connect(dsn, autocommit=True)
    try:
        repository = PostgresSchedulingJobRepository(verify)
        states: dict[str, int] = {}
        hashes: set[str] = set()
        results_found = 0
        for job_id in submitted_at:
            row = verify.execute(
                "SELECT state FROM scheduling_jobs WHERE tenant_id=%s "
                "AND project_id=%s AND job_id=%s",
                (tenant, "project-bench", job_id),
            ).fetchone()
            state = row[0] if row else "MISSING"
            states[state] = states.get(state, 0) + 1
            if state == SchedulingJobState.SUCCEEDED.value:
                result = repository.get_result(tenant, "project-bench", job_id)
                if result is not None:
                    results_found += 1
                    hashes.add(result.output_hash)
        pending = repository.count_pending(tenant_id=tenant)
    finally:
        _cleanup(verify, tenant)
        verify.close()

    expected = canonical_hash(
        date_schedule_payload(
            run_date_schedule(date_network(args.size, "dag", args.seed))
        )
    )
    cpu_seconds = sum(float(item["cpu_s"]) for item in summaries)
    worker_peak = max((int(item["peak_rss_kb"]) for item in summaries), default=0)
    worker_peak_sum = sum(int(item["peak_rss_kb"]) for item in summaries)
    succeeded = states.get(SchedulingJobState.SUCCEEDED.value, 0)

    return {
        "workers_requested": workers,
        "workers_supplied": min(workers, max(1, int(capacity.effective_cores))),
        "oversubscribed": workers > int(capacity.effective_cores),
        "budget_per_process": 1,
        "derived_host_budget": policy_budget.as_dict(),
        "jobs": args.jobs,
        "fixture_size": args.size,
        "wall_ms": round(wall * 1000.0, 3),
        "throughput_jobs_per_s": round(args.jobs / wall, 3) if wall > 0 else None,
        "states": states,
        "pending_after_drain": pending,
        "results_found": results_found,
        "canonical_hash": expected,
        "output_hashes_observed": sorted(hashes),
        "output_matches_engine": hashes == {expected},
        "latency_ms": _summary(latency),
        "queue_wait_ms": _summary(queue_wait),
        "run_ms": _summary(run_ms),
        "cpu_seconds_total": round(cpu_seconds, 3),
        "cpu_utilisation_cores": round(cpu_seconds / wall, 3) if wall > 0 else None,
        "worker_peak_rss_kb_max": worker_peak,
        "worker_peak_rss_kb_sum": worker_peak_sum,
        "worker_summaries": summaries,
        "event_count": len(events),
        "ok": (
            succeeded == args.jobs
            and pending == 0
            and hashes == {expected}
            and all(process.exitcode == 0 for process in processes)
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--dsn",
        default=os.environ.get("P6_TEST_POSTGRES_DSN"),
        help="PostgreSQL DSN; defaults to P6_TEST_POSTGRES_DSN",
    )
    parser.add_argument("--workers", default="1,2,4", help="comma list of worker counts")
    parser.add_argument("--jobs", type=int, default=32)
    parser.add_argument("--size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20261116)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--allow-oversubscription", action="store_true")
    parser.add_argument("--git-sha", default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    if not args.dsn:
        parser.error("--dsn or P6_TEST_POSTGRES_DSN is required")
    counts = [int(part) for part in args.workers.replace(" ", "").split(",") if part]
    if not counts or any(count < 1 for count in counts):
        parser.error("--workers must be a comma list of positive integers")
    if args.jobs < 1 or args.size < 1:
        parser.error("--jobs and --size must be positive")

    capacity = detect_effective_capacity()
    policy = WorkerBudgetPolicy()
    derived = policy.compute(capacity)
    suppliable = max(1, int(capacity.effective_cores))

    runs: list[dict[str, object]] = []
    for workers in counts:
        if workers > suppliable and not args.allow_oversubscription:
            runs.append(
                {
                    "workers_requested": workers,
                    "status": "refused",
                    "reason": (
                        f"HOST_SUPPLIES_ONLY_{suppliable}_EFFECTIVE_CORES; "
                        "pass --allow-oversubscription to measure informational oversubscription"
                    ),
                }
            )
            continue
        record = _run(args, workers, capacity, derived)
        record["status"] = "ok" if record["ok"] else "failed"
        runs.append(record)
        print(json.dumps({key: record[key] for key in (
            "workers_requested", "status", "wall_ms", "throughput_jobs_per_s",
            "latency_ms", "queue_wait_ms", "cpu_utilisation_cores",
            "output_matches_engine",
        )}, sort_keys=True), flush=True)

    document = {
        "environment": environment_fingerprint(args.git_sha),
        "capacity": capacity.as_dict(),
        "derived_budget": derived.as_dict(),
        "suppliable_workers": suppliable,
        "oversubscription_allowed": args.allow_oversubscription,
        "engine_version": ENGINE,
        "calculation_identity": CALCULATION,
        "jobs": args.jobs,
        "fixture_size": args.size,
        "seed": args.seed,
        "runs": runs,
    }
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote {args.out}", file=sys.stderr)
    return 0 if all(run.get("status") == "ok" for run in runs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
