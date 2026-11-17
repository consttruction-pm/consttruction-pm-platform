#!/usr/bin/env python3
"""P0-J phase 5: Scheduling Job stress with real PostgreSQL and real workers.

This harness stresses the *queue, database and worker path*, not the engine.
A fixed small fixture is deliberate: the point is submission, de-duplication,
claiming, lease renewal, cancellation, retry and result persistence under
concurrent virtual users. Pure-engine scaling is measured separately by
``scripts/scheduling_core_benchmark.py`` and ``scripts/p0j_float_parallel.py``.

Each virtual user runs the same scripted journey against the real lifecycle:

    submit -> poll status -> optionally cancel -> optionally resubmit

Workers are real OS processes running ``SchedulingJobExecutor`` over the same
PostgreSQL queue, exactly like the production worker.

    P6_TEST_POSTGRES_DSN=postgresql://... \
      python3 scripts/p0j_job_stress.py --users 100,500,1000 \
        --workers 1,2,4 --out <evidence-dir>

The host has 4 effective CPUs. A requested worker count above that is recorded
as oversubscribed and is never presented as real capacity.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import queue as queue_module
import statistics
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

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
    WorkerBudgetPolicy,
    detect_effective_capacity,
)
from construction_pm.scheduling_job_lifecycle import (  # noqa: E402
    SchedulingJobRequest,
    SchedulingJobService,
    SchedulingJobState,
)
from scheduling_worker_benchmark import (  # noqa: E402
    CALCULATION as WORKER_CALCULATION,
    ENGINE,
    _worker_main,
)

CALCULATION = "p0j-job-stress"
PROJECT = "project-p0j-stress"


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
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


def _virtual_user(
    service: SchedulingJobService,
    tenant: str,
    *,
    user_index: int,
    polls: int,
    poll_interval: float,
    cancel_fraction: float,
    resubmit: bool,
    metrics: dict[str, list[float]],
    outcomes: dict[str, int],
    errors: list[str],
) -> None:
    user = f"user-{user_index:05d}"
    should_cancel = (user_index % 100) < int(round(cancel_fraction * 100))

    def submit(fingerprint: str) -> str:
        start = time.perf_counter()
        try:
            submission = service.submit(
                SchedulingJobRequest(
                    tenant_id=tenant,
                    project_id=PROJECT,
                    submitted_by=user,
                    request_fingerprint=fingerprint,
                    engine_version=ENGINE,
                    calculation_identity=WORKER_CALCULATION,
                    max_attempts=2,
                )
            )
            metrics["submit_ms"].append((time.perf_counter() - start) * 1000.0)
            outcomes["submitted"] += 1
            return submission.job.job_id
        except Exception as error:  # noqa: BLE001 - counted, then re-raised
            errors.append(f"{user}:submit:{type(error).__name__}:{error}")
            raise

    def poll(job_id: str) -> str:
        state = "UNKNOWN"
        for _ in range(max(1, polls)):
            start = time.perf_counter()
            job = service.get(
                tenant_id=tenant, project_id=PROJECT, job_id=job_id, user_id=user
            )
            metrics["status_ms"].append((time.perf_counter() - start) * 1000.0)
            state = job.state.value
            if job.is_terminal:
                return state
            time.sleep(poll_interval)
        outcomes["poll_timeout"] += 1
        return state

    for attempt in range(2 if resubmit else 1):
        job_id = submit(f"{user}-{attempt}")
        if should_cancel and attempt == 0:
            start = time.perf_counter()
            job = service.cancel(
                tenant_id=tenant, project_id=PROJECT, job_id=job_id, user_id=user
            )
            metrics["cancel_ms"].append((time.perf_counter() - start) * 1000.0)
            outcomes["cancel_requested"] += 1
            if job.state is SchedulingJobState.CANCELLED:
                outcomes["cancelled_terminal"] += 1
                continue
        state = poll(job_id)
        outcomes[state.lower()] += 1
        if state == SchedulingJobState.CANCELLED.value and attempt == 0 and resubmit:
            continue
        break


def _run_case(
    *,
    dsn: str,
    users: int,
    workers: int,
    jobs_size: int,
    seed: int,
    timeout: float,
    polls: int,
    poll_interval: float,
    cancel_fraction: float,
    resubmit: bool,
    oversubscribed: bool,
    client_pool: int = 16,
) -> dict[str, object]:
    import psycopg

    tenant = f"p0j-stress-{uuid.uuid4()}"
    setup = psycopg.connect(dsn, autocommit=True)
    try:
        repository = PostgresSchedulingJobRepository(setup)
        repository.initialize()
        _cleanup(setup, tenant)
    finally:
        setup.close()

    # Virtual users borrow a bounded client connection pool, the way an
    # application server would. Each connection owns its own service instance,
    # so the measurement includes real connection/queue pressure instead of
    # serialising every user behind one shared connection.
    client_pool_size = max(1, min(users, client_pool))
    clients: "queue_module.Queue" = queue_module.Queue()
    client_connections = []
    for _ in range(client_pool_size):
        connection = psycopg.connect(dsn, autocommit=True)
        client_connections.append(connection)
        clients.put(
            SchedulingJobService(
                PostgresSchedulingJobRepository(connection),
                lease_ttl=timedelta(seconds=max(60.0, timeout)),
            )
        )

    context = multiprocessing.get_context("fork")
    queue = context.Queue()
    config = {
        "dsn": dsn,
        "size": jobs_size,
        "seed": seed,
        "timeout": timeout,
        "lease_ttl": max(60.0, timeout),
        "budget_per_process": 1,
    }
    processes = [
        context.Process(target=_worker_main, args=(config, queue))
        for _ in range(workers)
    ]

    connections: list[int] = []
    stop_monitor = threading.Event()

    def monitor() -> None:
        connection = psycopg.connect(dsn, autocommit=True)
        try:
            while not stop_monitor.is_set():
                row = connection.execute(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
                ).fetchone()
                connections.append(int(row[0]))
                stop_monitor.wait(0.05)
        finally:
            connection.close()

    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()

    wall_start = time.perf_counter()
    for process in processes:
        process.start()

    metrics: dict[str, list[float]] = {
        "submit_ms": [],
        "status_ms": [],
        "cancel_ms": [],
    }
    outcomes: dict[str, int] = {
        "submitted": 0,
        "poll_timeout": 0,
        "cancel_requested": 0,
        "cancelled_terminal": 0,
        "queued": 0,
        "leased": 0,
        "succeeded": 0,
        "failed": 0,
        "cancelled": 0,
    }
    errors: list[str] = []
    user_latency: list[float] = []
    pool_wait: list[float] = []

    def journey(index: int) -> None:
        started = time.perf_counter()
        wait_start = time.perf_counter()
        service = clients.get()
        pool_wait.append((time.perf_counter() - wait_start) * 1000.0)
        try:
            _virtual_user(
                service,
                tenant,
                user_index=index,
                polls=polls,
                poll_interval=poll_interval,
                cancel_fraction=cancel_fraction,
                resubmit=resubmit,
                metrics=metrics,
                outcomes=outcomes,
                errors=errors,
            )
        finally:
            clients.put(service)
        user_latency.append((time.perf_counter() - started) * 1000.0)

    with ThreadPoolExecutor(max_workers=users) as pool:
        list(pool.map(journey, range(users)))

    for process in processes:
        process.join(timeout)
    wall = time.perf_counter() - wall_start
    stop_monitor.set()
    monitor_thread.join(1.0)
    for connection in client_connections:
        connection.close()

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
    run_ms = [
        float(event["run_ms"])
        for event in events
        if event["kind"] in {"SUCCEEDED", "FAILED", "CANCELLED"}
        and event.get("run_ms") is not None
    ]

    verify = psycopg.connect(dsn, autocommit=True)
    try:
        repository = PostgresSchedulingJobRepository(verify)
        states: dict[str, int] = {}
        hashes: set[str] = set()
        results_found = 0
        for (job_id,) in verify.execute(
            "SELECT job_id FROM scheduling_jobs WHERE tenant_id=%s AND project_id=%s",
            (tenant, PROJECT),
        ).fetchall():
            row = verify.execute(
                "SELECT state FROM scheduling_jobs WHERE tenant_id=%s "
                "AND project_id=%s AND job_id=%s",
                (tenant, PROJECT, job_id),
            ).fetchone()
            state = row[0] if row else "MISSING"
            states[state] = states.get(state, 0) + 1
            if state == SchedulingJobState.SUCCEEDED.value:
                result = repository.get_result(tenant, PROJECT, job_id)
                if result is not None:
                    results_found += 1
                    hashes.add(result.output_hash)
        pending = repository.count_pending(tenant_id=tenant)
        total_jobs = sum(states.values())
    finally:
        _cleanup(verify, tenant)
        verify.close()

    expected = canonical_hash(
        date_schedule_payload(
            run_date_schedule(date_network(jobs_size, "dag", seed))
        )
    )
    cpu_seconds = sum(float(item["cpu_s"]) for item in summaries)
    worker_peak = max((int(item["peak_rss_kb"]) for item in summaries), default=0)
    succeeded = states.get(SchedulingJobState.SUCCEEDED.value, 0)
    cancelled = states.get(SchedulingJobState.CANCELLED.value, 0)
    failed = states.get(SchedulingJobState.FAILED.value, 0)

    return {
        "users": users,
        "workers_requested": workers,
        "oversubscribed": oversubscribed,
        "jobs_created": total_jobs,
        "wall_ms": round(wall * 1000.0, 3),
        "journey_throughput_users_per_s": round(users / wall, 3) if wall else None,
        "job_throughput_jobs_per_s": round(total_jobs / wall, 3) if wall else None,
        "states": states,
        "results_found": results_found,
        "pending_after_drain": pending,
        "canonical_hash": expected,
        "output_hashes_observed": sorted(hashes),
        "output_matches_engine": hashes == {expected},
        "success_failure_cancel_counts": {
            "succeeded": succeeded,
            "failed": failed,
            "cancelled": cancelled,
        },
        "scripted_outcomes": outcomes,
        "errors": errors[:50],
        "error_count": len(errors),
        "submit_ms": _summary(metrics["submit_ms"]),
        "status_ms": _summary(metrics["status_ms"]),
        "cancel_ms": _summary(metrics["cancel_ms"]),
        "journey_ms": _summary(user_latency),
        "client_pool_size": client_pool_size,
        "client_pool_wait_ms": _summary(pool_wait),
        "queue_wait_ms": _summary(queue_wait),
        "run_ms": _summary(run_ms),
        "cpu_seconds_total": round(cpu_seconds, 3),
        "cpu_utilisation_cores": round(cpu_seconds / wall, 3) if wall else None,
        "worker_peak_rss_kb_max": worker_peak,
        "worker_summaries": summaries,
        "pg_connections_max": max(connections, default=None),
        "pg_connections_median": (
            round(statistics.median(connections), 3) if connections else None
        ),
        "pg_samples": len(connections),
        "worker_exitcodes": [process.exitcode for process in processes],
        "ok": (
            not errors
            and pending == 0
            and hashes == {expected}
            and all(process.exitcode == 0 for process in processes)
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dsn", default=os.environ.get("P6_TEST_POSTGRES_DSN"))
    parser.add_argument("--users", default="100,500,1000")
    parser.add_argument("--workers", default="1,2,4")
    parser.add_argument("--size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20261117)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--polls", type=int, default=40)
    parser.add_argument("--poll-interval", type=float, default=0.02)
    parser.add_argument("--cancel-fraction", type=float, default=0.1)
    parser.add_argument("--no-resubmit", action="store_true")
    parser.add_argument("--client-pool", type=int, default=16)
    parser.add_argument("--allow-oversubscription", action="store_true")
    parser.add_argument("--git-sha", default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    if not args.dsn:
        parser.error("--dsn or P6_TEST_POSTGRES_DSN is required")
    user_counts = [int(value) for value in args.users.split(",") if value]
    worker_counts = [int(value) for value in args.workers.split(",") if value]
    if not user_counts or not worker_counts or args.size < 1:
        parser.error("--users/--workers must be lists and --size must be positive")

    capacity = detect_effective_capacity()
    derived = WorkerBudgetPolicy().compute(capacity)
    suppliable = max(1, int(capacity.effective_cores))

    runs: list[dict[str, object]] = []
    for users in user_counts:
        for workers in worker_counts:
            if workers > suppliable and not args.allow_oversubscription:
                runs.append(
                    {
                        "users": users,
                        "workers_requested": workers,
                        "status": "refused",
                        "reason": (
                            f"HOST_SUPPLIES_ONLY_{suppliable}_EFFECTIVE_CORES; "
                            "pass --allow-oversubscription to record it as simulated"
                        ),
                    }
                )
                continue
            print(f"users={users} workers={workers} ...", flush=True)
            record = _run_case(
                dsn=args.dsn,
                users=users,
                workers=workers,
                jobs_size=args.size,
                seed=args.seed,
                timeout=args.timeout,
                polls=args.polls,
                poll_interval=args.poll_interval,
                cancel_fraction=args.cancel_fraction,
                resubmit=not args.no_resubmit,
                oversubscribed=workers > suppliable,
                client_pool=args.client_pool,
            )
            record["status"] = "ok" if record["ok"] else "failed"
            runs.append(record)
            print(
                json.dumps(
                    {
                        key: record[key]
                        for key in (
                            "users",
                            "workers_requested",
                            "status",
                            "wall_ms",
                            "job_throughput_jobs_per_s",
                            "submit_ms",
                            "status_ms",
                            "journey_ms",
                            "client_pool_wait_ms",
                            "queue_wait_ms",
                            "pg_connections_max",
                            "states",
                            "error_count",
                            "output_matches_engine",
                        )
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    document = {
        "environment": environment_fingerprint(args.git_sha),
        "capacity": capacity.as_dict(),
        "derived_budget": derived.as_dict(),
        "suppliable_workers": suppliable,
        "oversubscription_allowed": args.allow_oversubscription,
        "engine_version": ENGINE,
        "calculation_identity": WORKER_CALCULATION,
        "stress_label": CALCULATION,
        "fixture_size": args.size,
        "seed": args.seed,
        "cancel_fraction": args.cancel_fraction,
        "resubmit": not args.no_resubmit,
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
