"""Tests for P0-G adaptive execution of durable scheduling jobs."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

from construction_pm.scheduling.benchmark_fixtures import (
    canonical_hash,
    date_network,
    date_schedule_payload,
    run_date_schedule,
)
from construction_pm.scheduling_execution_budget import (
    AdaptiveWorkerController,
    GlobalExecutionBudget,
)
from construction_pm.scheduling_job_executor import (
    SchedulingExecutionError,
    SchedulingJobExecutor,
)
from construction_pm.scheduling_job_lifecycle import (
    InMemorySchedulingJobRepository,
    SchedulingJobRequest,
    SchedulingJobResult,
    SchedulingJobResultError,
    SchedulingJobService,
    SchedulingJobState,
)


TENANT = "tenant-p0g"
PROJECT = "project-p0g"
ENGINE = "cubi-26.0.0"
CALCULATION = "calc-2026-11-16"
FIXTURE = date_network(30)
CANONICAL_HASH = canonical_hash(date_schedule_payload(run_date_schedule(FIXTURE)))


def _service(lease_ttl: timedelta = timedelta(seconds=30)) -> SchedulingJobService:
    return SchedulingJobService(
        InMemorySchedulingJobRepository(), lease_ttl=lease_ttl
    )


def _request(fingerprint: str, *, max_attempts: int = 3) -> SchedulingJobRequest:
    return SchedulingJobRequest(
        tenant_id=TENANT,
        project_id=PROJECT,
        submitted_by="alice",
        request_fingerprint=fingerprint,
        engine_version=ENGINE,
        calculation_identity=CALCULATION,
        max_attempts=max_attempts,
    )


def _result(job, output_hash: str = CANONICAL_HASH) -> SchedulingJobResult:
    return SchedulingJobResult(
        tenant_id=job.tenant_id,
        project_id=job.project_id,
        job_id=job.job_id,
        engine_version=job.engine_version,
        calculation_identity=job.calculation_identity,
        output_hash=output_hash,
        payload={"activities": len(FIXTURE.activities), "floats": 0},
        persisted_at=datetime.now(timezone.utc),
    )


def _engine_calculate(job) -> SchedulingJobResult:
    """Run the real authoritative engine and hash its canonical payload."""
    schedule_result = run_date_schedule(FIXTURE)
    output_hash = canonical_hash(date_schedule_payload(schedule_result))
    assert output_hash == CANONICAL_HASH
    return _result(job, output_hash)


def _get(service: SchedulingJobService, job_id: str):
    return service.get(
        tenant_id=TENANT, project_id=PROJECT, job_id=job_id, user_id="alice"
    )


def test_executor_drains_the_queue_with_the_real_engine_hash():
    service = _service()
    job_ids = [
        service.submit(_request(f"fp-{index}")).job.job_id for index in range(6)
    ]
    executor = SchedulingJobExecutor(
        service,
        calculate=_engine_calculate,
        owner="worker-a",
        budget=GlobalExecutionBudget(2),
        poll_interval=0.005,
    )

    summary = executor.run_until_idle(timeout=60)

    assert summary.claimed == 6
    assert summary.succeeded == 6
    assert summary.failed == 0
    assert summary.skipped == 0
    for job_id in job_ids:
        job = _get(service, job_id)
        assert job.state is SchedulingJobState.SUCCEEDED
        stored = service.get_result(
            tenant_id=TENANT, project_id=PROJECT, job_id=job_id, user_id="alice"
        )
        assert stored.output_hash == CANONICAL_HASH
        assert stored.payload == {"activities": 30, "floats": 0}


def test_worker_counts_one_two_and_four_produce_identical_output():
    observed: dict[int, list[str]] = {}
    for workers in (1, 2, 4):
        service = _service()
        job_ids = [
            service.submit(_request(f"fp-{workers}-{index}")).job.job_id
            for index in range(5)
        ]
        budget = GlobalExecutionBudget(workers)
        executor = SchedulingJobExecutor(
            service,
            calculate=_engine_calculate,
            owner=f"worker-{workers}",
            budget=budget,
            poll_interval=0.002,
        )
        summary = executor.run_until_idle(timeout=60)
        assert summary.succeeded == 5
        assert budget.peak <= workers
        observed[workers] = [
            service.get_result(
                tenant_id=TENANT, project_id=PROJECT, job_id=job_id, user_id="alice"
            ).output_hash
            for job_id in job_ids
        ]

    assert observed[1] == observed[2] == observed[4]
    assert set(observed[1]) == {CANONICAL_HASH}


def test_one_global_budget_caps_two_executors_together():
    repository = InMemorySchedulingJobRepository()
    left = SchedulingJobService(repository, lease_ttl=timedelta(seconds=30))
    right = SchedulingJobService(repository, lease_ttl=timedelta(seconds=30))
    for index in range(10):
        left.submit(_request(f"fp-{index}"))

    budget = GlobalExecutionBudget(2)
    lock = threading.Lock()
    active = 0
    peak = 0

    def calculate(job) -> SchedulingJobResult:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            time.sleep(0.02)
        finally:
            with lock:
                active -= 1
        return _result(job)

    executors = [
        SchedulingJobExecutor(
            service,
            calculate=calculate,
            owner=f"worker-{name}",
            budget=budget,
            poll_interval=0.002,
        )
        for name, service in (("left", left), ("right", right))
    ]
    threads = [
        threading.Thread(target=lambda executor=executor: executor.run_until_idle(timeout=60))
        for executor in executors
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert peak <= 2
    assert budget.peak <= 2
    jobs = repository.find_queued(100)
    assert jobs == ()
    assert repository.count_pending() == 0


def test_retryable_failure_requeues_then_succeeds():
    service = _service()
    submission = service.submit(_request("fp-retry", max_attempts=2))
    attempts: dict[str, int] = {}

    def calculate(job) -> SchedulingJobResult:
        attempts[job.job_id] = attempts.get(job.job_id, 0) + 1
        if attempts[job.job_id] == 1:
            raise SchedulingExecutionError("TRANSIENT_DB_READ", retryable=True)
        return _result(job)

    executor = SchedulingJobExecutor(
        service,
        calculate=calculate,
        owner="worker-a",
        budget=GlobalExecutionBudget(1),
        poll_interval=0.002,
    )
    summary = executor.run_until_idle(timeout=30)

    assert summary.retried == 1
    assert summary.succeeded == 1
    assert summary.claimed == 2
    queued = service.queued_jobs(10)
    assert queued == ()
    assert len(attempts) == 1
    finished = _get(service, submission.job.job_id)
    assert finished.state is SchedulingJobState.SUCCEEDED
    assert finished.attempts == 2


def test_non_retryable_failure_is_terminal_and_publishes_no_result():
    service = _service()
    submission = service.submit(_request("fp-bad"))

    def calculate(job):
        raise ValueError("SNAPSHOT_CORRUPT")

    executor = SchedulingJobExecutor(
        service,
        calculate=calculate,
        owner="worker-a",
        budget=GlobalExecutionBudget(1),
        poll_interval=0.002,
    )
    summary = executor.run_until_idle(timeout=30)

    assert summary.failed == 1
    job = _get(service, submission.job.job_id)
    assert job.state is SchedulingJobState.FAILED
    assert "SNAPSHOT_CORRUPT" in (job.last_error or "")
    with pytest.raises(SchedulingJobResultError):
        service.get_result(
            tenant_id=TENANT,
            project_id=PROJECT,
            job_id=submission.job.job_id,
            user_id="alice",
        )


def test_cancellation_while_calculating_never_publishes_a_result():
    service = _service(lease_ttl=timedelta(seconds=0.6))
    submission = service.submit(_request("fp-cancel"))
    started = threading.Event()
    release = threading.Event()

    def calculate(job) -> SchedulingJobResult:
        started.set()
        release.wait(10)
        return _result(job)

    executor = SchedulingJobExecutor(
        service,
        calculate=calculate,
        owner="worker-a",
        budget=GlobalExecutionBudget(1),
        poll_interval=0.01,
    )
    thread = threading.Thread(target=executor.run_until_idle, kwargs={"timeout": 30})
    thread.start()
    assert started.wait(10)

    service.cancel(
        tenant_id=TENANT, project_id=PROJECT, job_id=submission.job.job_id, user_id="alice"
    )
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if _get(service, submission.job.job_id).cancel_requested:
            break
        time.sleep(0.01)
    # Let the lease heartbeat observe the cancellation before the result exists.
    time.sleep(0.8)
    release.set()
    thread.join(timeout=30)
    assert not thread.is_alive()

    job = _get(service, submission.job.job_id)
    assert job.state is SchedulingJobState.CANCELLED
    with pytest.raises(SchedulingJobResultError):
        service.get_result(
            tenant_id=TENANT,
            project_id=PROJECT,
            job_id=submission.job.job_id,
            user_id="alice",
        )


def test_engine_identity_mismatch_is_terminal_before_any_calculation():
    service = _service()
    submission = service.submit(_request("fp-engine"))
    called = threading.Event()

    def calculate(job):
        called.set()
        return _result(job)

    executor = SchedulingJobExecutor(
        service,
        calculate=calculate,
        owner="worker-a",
        budget=GlobalExecutionBudget(1),
        engine_identity=("cubi-25.0.0", CALCULATION),
        poll_interval=0.002,
    )
    summary = executor.run_until_idle(timeout=30)

    assert summary.failed == 1
    assert not called.is_set()
    job = _get(service, submission.job.job_id)
    assert job.state is SchedulingJobState.FAILED
    assert "ENGINE_IDENTITY_MISMATCH" in (job.last_error or "")


def test_adaptive_target_limits_dispatch_below_the_hard_budget():
    service = _service()
    for index in range(8):
        service.submit(_request(f"fp-{index}"))

    budget = GlobalExecutionBudget(4)
    controller = AdaptiveWorkerController(maximum=2)
    lock = threading.Lock()
    active = 0
    peak = 0

    def calculate(job) -> SchedulingJobResult:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            time.sleep(0.01)
        finally:
            with lock:
                active -= 1
        return _result(job)

    executor = SchedulingJobExecutor(
        service,
        calculate=calculate,
        owner="worker-a",
        budget=budget,
        controller=controller,
        poll_interval=0.002,
    )
    summary = executor.run_until_idle(timeout=60)

    assert summary.succeeded == 8
    assert peak <= 2
    assert budget.peak <= 2


def test_run_once_returns_false_when_the_queue_is_empty():
    service = _service()
    executor = SchedulingJobExecutor(
        service,
        calculate=_engine_calculate,
        owner="worker-a",
        budget=GlobalExecutionBudget(1),
        poll_interval=0.0,
    )
    assert executor.run_once() is False
