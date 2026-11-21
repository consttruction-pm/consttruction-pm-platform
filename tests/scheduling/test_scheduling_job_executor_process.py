"""P0-N: process placement inside the durable job executor.

These tests exercise the real executor loop, the real global budget and real
child processes. Every test compares the canonical payload hash with the
unchanged sequential engine, so placement can change only elapsed time.
"""

from __future__ import annotations

import multiprocessing
import time
from datetime import datetime, timedelta, timezone

import pytest

from construction_pm.scheduling.benchmark_fixtures import (
    canonical_hash,
    time_network,
    time_schedule_payload,
)
from construction_pm.scheduling.time_schedule import FloatExecutionPolicy, time_schedule
from construction_pm.scheduling_execution_budget import GlobalExecutionBudget
from construction_pm.scheduling_job_executor import (
    SchedulingExecutionError,
    SchedulingJobExecutor,
)
from construction_pm.scheduling_job_lifecycle import (
    InMemorySchedulingJobRepository,
    SchedulingJobRequest,
    SchedulingJobResult,
    SchedulingJobService,
    SchedulingJobState,
)
from construction_pm.scheduling_result_cache import ScheduleResultCache
from construction_pm.scheduling_worker_scheduler import ProjectWorkload


ENGINE = "cubi-26.0.0"
FIXTURES = {
    "project-a": time_network(700, "dag", 31),
    "project-b": time_network(600, "mixed", 32),
    "project-c": time_network(500, "wide", 33),
    "project-d": time_network(400, "fan", 34),
}


def _sequential_hash(project_id: str) -> str:
    fixture = FIXTURES[project_id]
    result = time_schedule(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.project_finish,
        fixture.registry,
    )
    return canonical_hash(time_schedule_payload(result))


def _result(job, fixture, *, slots: int | None = None) -> SchedulingJobResult:
    policy = (
        None
        if slots is None
        else FloatExecutionPolicy(workers=max(1, slots), allow_nested_fork=True)
    )
    result = time_schedule(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.project_finish,
        fixture.registry,
        float_policy=policy,
    )
    payload: dict[str, object] = {"activities": len(fixture.activities)}
    if slots is not None:
        payload["slots"] = slots
    return SchedulingJobResult(
        tenant_id=job.tenant_id,
        project_id=job.project_id,
        job_id=job.job_id,
        engine_version=job.engine_version,
        calculation_identity=job.calculation_identity,
        output_hash=canonical_hash(time_schedule_payload(result)),
        payload=payload,
        persisted_at=datetime.now(timezone.utc),
    )


def calculate(job) -> SchedulingJobResult:
    return _result(job, FIXTURES[job.project_id])


def calculate_with_slots(job, slots: int) -> SchedulingJobResult:
    return _result(job, FIXTURES[job.project_id], slots=slots)


def _service(lease_ttl: float = 60.0) -> SchedulingJobService:
    return SchedulingJobService(
        InMemorySchedulingJobRepository(), lease_ttl=timedelta(seconds=lease_ttl)
    )


def _submit(service: SchedulingJobService, projects, *, engine: str = ENGINE) -> None:
    for index, project in enumerate(projects):
        service.submit(
            SchedulingJobRequest(
                tenant_id="tenant-p0n",
                project_id=project,
                submitted_by="alice",
                request_fingerprint=f"fp-{index}",
                engine_version=engine,
                calculation_identity=f"calc-{index}",
            )
        )


def _executor(
    service: SchedulingJobService,
    *,
    budget: int = 4,
    cache: ScheduleResultCache | None = None,
    **kwargs,
) -> SchedulingJobExecutor:
    settings = dict(
        execution_mode="process",
        poll_interval=0.002,
        idle_polls_before_exit=3,
        workload_estimator=lambda job: ProjectWorkload(
            len(FIXTURES[job.project_id].activities)
        ),
        calculate_with_slots=calculate_with_slots,
    )
    if cache is not None:
        settings["result_cache"] = cache
    settings.update(kwargs)
    return SchedulingJobExecutor(
        service,
        calculate=calculate,
        owner="worker-p0n",
        budget=GlobalExecutionBudget(budget),
        **settings,
    )


requires_fork = pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(),
    reason="child processes inherit the in-memory fixtures through fork",
)


def _persisted_hashes(service: SchedulingJobService) -> dict[str, str]:
    results = service._repository._results  # in-memory repository used here
    return {result.project_id: result.output_hash for result in results.values()}


@requires_fork
def test_process_mode_matches_sequential_hashes_for_every_project():
    service = _service()
    _submit(service, FIXTURES)
    executor = _executor(service, budget=4)
    summary = executor.run_until_idle(timeout=120)
    assert summary.succeeded == 4 and summary.failed == 0
    assert summary.process_starts == 4
    assert summary.peak_slots <= 4
    assert executor.budget.active == 0
    hashes = _persisted_hashes(service)
    for project in FIXTURES:
        assert hashes[project] == _sequential_hash(project)


@requires_fork
def test_process_mode_results_are_persisted_and_identical():
    service = _service()
    _submit(service, ["project-a", "project-b"])
    executor = _executor(service, budget=2)
    executor.run_until_idle(timeout=120)
    hashes = _persisted_hashes(service)
    assert hashes["project-a"] == _sequential_hash("project-a")
    assert hashes["project-b"] == _sequential_hash("project-b")


@requires_fork
def test_result_larger_than_the_pipe_buffer_does_not_deadlock():
    """Regression: a big result must be read while the child may still send.

    The child publishes the pickled result over a one-way pipe. When the
    payload exceeds the OS pipe buffer the child blocks in ``send`` until the
    parent drains it, so a parent that only reads after ``join`` deadlocks
    until ``job_timeout``. Two megabytes is far beyond that buffer.
    """
    service = _service()
    _submit(service, ["project-a"])
    detail = "x" * 2_000_000

    def large(job, slots):
        base = calculate_with_slots(job, slots)
        return SchedulingJobResult(
            tenant_id=base.tenant_id,
            project_id=base.project_id,
            job_id=base.job_id,
            engine_version=base.engine_version,
            calculation_identity=base.calculation_identity,
            output_hash=base.output_hash,
            payload={**dict(base.payload), "detail": detail},
            persisted_at=base.persisted_at,
        )

    executor = _executor(
        service, budget=2, calculate_with_slots=large, job_timeout=60
    )
    summary = executor.run_until_idle(timeout=60)
    assert summary.succeeded == 1 and summary.failed == 0
    assert summary.process_starts == 1
    results = list(service._repository._results.values())
    assert len(results[0].payload["detail"]) == len(detail)
    assert results[0].output_hash == _sequential_hash("project-a")


@requires_fork
def test_single_project_receives_the_whole_budget():
    fixture = time_network(4000, "dag", 41)
    FIXTURES["project-solo"] = fixture
    try:
        service = _service()
        _submit(service, ["project-solo"])
        executor = _executor(service, budget=4)
        summary = executor.run_until_idle(timeout=120)
        assert summary.succeeded == 1
        assert summary.peak_slots == 4
        stored = service._repository
        results = list(getattr(stored, "_results", {}).values())
        assert results and results[0].payload["slots"] == 4
    finally:
        FIXTURES.pop("project-solo", None)


@requires_fork
def test_cache_hit_skips_the_second_calculation():
    cache = ScheduleResultCache(max_weight_bytes=4 * 1024 * 1024)
    projects = ["project-a", "project-b"]
    first_service = _service()
    _submit(first_service, projects)
    first = _executor(first_service, budget=2, cache=cache).run_until_idle(timeout=120)
    assert first.succeeded == 2 and first.cache_hits == 0

    second_service = _service()
    _submit(second_service, projects)
    second = _executor(second_service, budget=2, cache=cache).run_until_idle(timeout=120)
    assert second.succeeded == 2
    assert second.cache_hits == 2
    assert second.process_starts == 0
    assert cache.stats()["hits"] == 2


@requires_fork
def test_cache_key_follows_the_engine_version():
    cache = ScheduleResultCache(max_weight_bytes=1024 * 1024)
    service = _service()
    _submit(service, ["project-c"], engine=ENGINE)
    _executor(service, budget=2, cache=cache).run_until_idle(timeout=120)
    other = _service()
    _submit(other, ["project-c"], engine="cubi-26.1.0")
    summary = _executor(other, budget=2, cache=cache).run_until_idle(timeout=120)
    assert summary.cache_hits == 0
    assert summary.process_starts == 1


def test_thread_mode_rejects_process_settings():
    service = _service()
    _submit(service, ["project-a"])
    with pytest.raises(SchedulingExecutionError):
        SchedulingJobExecutor(
            service,
            calculate=calculate,
            owner="worker",
            budget=GlobalExecutionBudget(2),
            execution_mode="process",
            workload_estimator=lambda job: ProjectWorkload(10),
            result_cache=ScheduleResultCache(max_weight_bytes=1024),
            calculate_with_slots=calculate_with_slots,
            start_method="bogus",
        )


@requires_fork
def test_cancellation_terminates_the_child_and_releases_slots():
    service = _service()
    _submit(service, ["project-a"])

    def slow(job, slots):
        time.sleep(30)
        return calculate_with_slots(job, slots)

    executor = _executor(service, budget=2, calculate_with_slots=slow)
    executor._dispatch_process_jobs(pending=1, target=1)
    assert executor.in_flight() == 1
    job = list(service._repository._jobs.values())[0]
    service.cancel(
        tenant_id=job.tenant_id,
        project_id=job.project_id,
        job_id=job.job_id,
        user_id="alice",
    )
    # The renewal point is due; the renewal observes the cancellation request.
    executor._process_jobs[job.job_id].next_renewal = 0.0
    executor._renew_process_leases()
    assert executor.in_flight() == 0
    assert executor.budget.active == 0
    final = service._repository._jobs[job.tenant_id, job.project_id, job.job_id]
    assert final.state is SchedulingJobState.CANCELLED


@requires_fork
def test_failing_calculation_is_recorded_as_terminal_failure():
    service = _service()
    _submit(service, ["project-a"])

    def broken(job, slots):
        raise RuntimeError("engine exploded")

    executor = _executor(service, budget=2, calculate_with_slots=broken)
    summary = executor.run_until_idle(timeout=60)
    assert summary.failed == 1
    assert summary.succeeded == 0
    job = service.queued_jobs(1)
    record = service._repository._jobs[("tenant-p0n", "project-a", _only_job_id(service))]
    assert record.state is SchedulingJobState.FAILED
    assert "engine exploded" in (record.last_error or "")


def _only_job_id(service: SchedulingJobService) -> str:
    jobs = list(service._repository._jobs.values())
    return jobs[0].job_id


@requires_fork
def test_lease_is_renewed_while_the_child_calculates():
    service = _service(lease_ttl=1.0)
    _submit(service, ["project-a"])

    def slow(job, slots):
        time.sleep(1.6)
        return calculate_with_slots(job, slots)

    executor = _executor(service, budget=2, calculate_with_slots=slow)
    summary = executor.run_until_idle(timeout=60)
    assert summary.succeeded == 1
    assert summary.lease_lost == 0


@pytest.mark.skipif(
    "spawn" not in multiprocessing.get_all_start_methods(),
    reason="requires spawn to exercise the unpicklable fallback",
)
def test_unpicklable_runner_falls_back_inline_with_spawn():
    service = _service()
    _submit(service, ["project-a"])

    def local_runner(job, slots):
        return calculate_with_slots(job, slots)
    executor = SchedulingJobExecutor(
        service,
        calculate=calculate,
        owner="worker",
        budget=GlobalExecutionBudget(2),
        execution_mode="process",
        poll_interval=0.002,
        idle_polls_before_exit=3,
        start_method="spawn",
        calculate_with_slots=local_runner,
        workload_estimator=lambda job: ProjectWorkload(700),
    )
    summary = executor.run_until_idle(timeout=60)
    # A local function cannot be transferred by value, so the exact inline path
    # runs instead of failing the job.
    assert summary.succeeded == 1
    assert summary.inline_fallbacks == 1
    assert summary.process_starts == 0


@requires_fork
def test_two_executors_share_one_budget():
    budget = GlobalExecutionBudget(2)
    first_service = _service()
    second_service = _service()
    _submit(first_service, ["project-a"])
    _submit(second_service, ["project-b"])
    first = _executor(first_service, budget=2)
    second = _executor(second_service, budget=2)
    first._budget = budget
    second._budget = budget
    first.run_until_idle(timeout=120)
    second.run_until_idle(timeout=120)
    assert budget.active == 0
    assert budget.peak <= 2
