"""P0-N: the process-mode executor on the PostgreSQL lifecycle adapter.

Placement must be independent of the persistence adapter. This file runs the
same executor loop, with real child processes, against the PostgreSQL
repository: every persisted output hash must equal the sequential engine, the
second evaluation of identical inputs must be served from the adaptive cache,
and a second tenant must not see the first tenant's results.

Set ``P6_TEST_POSTGRES_DSN`` to a reachable database; the tests skip otherwise.
"""

from __future__ import annotations

import multiprocessing
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from construction_pm.scheduling.benchmark_fixtures import (
    canonical_hash,
    time_network,
    time_schedule_payload,
)
from construction_pm.scheduling.time_schedule import FloatExecutionPolicy, time_schedule
from construction_pm.scheduling_execution_budget import GlobalExecutionBudget
from construction_pm.scheduling_job_executor import SchedulingJobExecutor
from construction_pm.scheduling_job_lifecycle import (
    SchedulingJobRequest,
    SchedulingJobResult,
    SchedulingJobService,
)
from construction_pm.scheduling_result_cache import ScheduleResultCache
from construction_pm.scheduling_worker_scheduler import ProjectWorkload
from construction_pm.postgres_scheduling_job_lifecycle import (
    PostgresSchedulingJobRepository,
)

pytestmark = pytest.mark.postgres

ENGINE = "cubi-26.0.0"
FIXTURES = {
    "project-alpha": time_network(700, "dag", 41),
    "project-beta": time_network(600, "mixed", 42),
    "project-gamma": time_network(500, "wide", 43),
}


def _dsn() -> str:
    dsn = os.getenv("P6_TEST_POSTGRES_DSN") or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    if not dsn:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    return dsn


def _connection():
    psycopg = pytest.importorskip("psycopg")
    return psycopg.connect(_dsn(), autocommit=True)


def _sequential(project_id: str) -> str:
    fixture = FIXTURES[project_id]
    result = time_schedule(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.project_finish,
        fixture.registry,
    )
    return canonical_hash(time_schedule_payload(result))


def _evaluate(job, slots: int | None) -> SchedulingJobResult:
    fixture = FIXTURES[job.project_id]
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
    return _evaluate(job, None)


def calculate_with_slots(job, slots: int) -> SchedulingJobResult:
    return _evaluate(job, slots)


def _submit(service: SchedulingJobService, tenant: str, project: str, identity: str) -> str:
    submission = service.submit(
        SchedulingJobRequest(
            tenant_id=tenant,
            project_id=project,
            submitted_by="alice",
            request_fingerprint=f"fp-{identity}",
            engine_version=ENGINE,
            calculation_identity=identity,
        )
    )
    return submission.job.job_id


def _executor(
    service: SchedulingJobService, *, budget: int, cache: ScheduleResultCache | None = None
) -> SchedulingJobExecutor:
    return SchedulingJobExecutor(
        service,
        calculate=calculate,
        owner="worker-p0n-pg",
        budget=GlobalExecutionBudget(budget),
        execution_mode="process",
        poll_interval=0.002,
        idle_polls_before_exit=3,
        workload_estimator=lambda job: ProjectWorkload(
            len(FIXTURES[job.project_id].activities)
        ),
        calculate_with_slots=calculate_with_slots,
        result_cache=cache,
    )


def _persisted_hashes(
    service: SchedulingJobService, tenant: str, job_ids: dict[str, str]
) -> dict[str, str]:
    hashes = {}
    for project, job_id in job_ids.items():
        result = service.get_result(
            tenant_id=tenant, project_id=project, job_id=job_id, user_id="alice"
        )
        hashes[project] = result.output_hash
    return hashes


requires_fork = pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(),
    reason="child processes inherit the in-memory fixtures through fork",
)


@requires_fork
def test_process_mode_persists_matching_hashes_on_postgres():
    tenant = f"p0n-{uuid.uuid4()}"
    with _connection() as connection:
        repository = PostgresSchedulingJobRepository(connection)
        repository.initialize()
        service = SchedulingJobService(repository, lease_ttl=timedelta(seconds=60))
        job_ids = {
            project: _submit(service, tenant, project, f"identity-{index}")
            for index, project in enumerate(FIXTURES)
        }

        summary = _executor(service, budget=4).run_until_idle(timeout=120)
        assert summary.succeeded == len(FIXTURES)
        assert summary.process_starts == len(FIXTURES)

        assert _persisted_hashes(service, tenant, job_ids) == {
            project: _sequential(project) for project in FIXTURES
        }


@requires_fork
def test_warm_cache_satisfies_a_second_postgres_run():
    tenant = f"p0n-{uuid.uuid4()}"
    with _connection() as connection:
        repository = PostgresSchedulingJobRepository(connection)
        repository.initialize()
        service = SchedulingJobService(repository, lease_ttl=timedelta(seconds=60))
        cache = ScheduleResultCache(max_weight_bytes=16 * 1024 * 1024)

        cold_ids = {
            project: _submit(service, tenant, project, f"cold-{index}")
            for index, project in enumerate(FIXTURES)
        }
        cold = _executor(service, budget=4, cache=cache).run_until_idle(timeout=120)
        assert cold.cache_hits == 0
        assert cold.succeeded == len(FIXTURES)

        # Same calculation identity and therefore the same cache key; the
        # first job is terminal, so this submission is a new job.
        warm_ids = {
            project: _submit(service, tenant, project, f"cold-{index}")
            for index, project in enumerate(FIXTURES)
        }
        warm = _executor(service, budget=4, cache=cache).run_until_idle(timeout=120)
        assert warm.cache_hits == len(FIXTURES)
        assert warm.process_starts == 0
        assert warm.succeeded == len(FIXTURES)

        cold_hashes = _persisted_hashes(service, tenant, cold_ids)
        warm_hashes = _persisted_hashes(service, tenant, warm_ids)
        assert warm_hashes == cold_hashes
        assert warm_hashes == {project: _sequential(project) for project in FIXTURES}


@requires_fork
def test_two_tenants_do_not_share_results_on_postgres():
    """Same project id and identity, different tenant: separate jobs and rows."""
    tenant_a = f"p0n-a-{uuid.uuid4()}"
    tenant_b = f"p0n-b-{uuid.uuid4()}"
    with _connection() as connection:
        repository = PostgresSchedulingJobRepository(connection)
        repository.initialize()
        service = SchedulingJobService(repository, lease_ttl=timedelta(seconds=60))
        a_id = _submit(service, tenant_a, "project-alpha", "shared")
        b_id = _submit(service, tenant_b, "project-alpha", "shared")
        assert a_id != b_id

        _executor(service, budget=4).run_until_idle(timeout=120)

        result_a = service.get_result(
            tenant_id=tenant_a, project_id="project-alpha", job_id=a_id, user_id="alice"
        )
        result_b = service.get_result(
            tenant_id=tenant_b, project_id="project-alpha", job_id=b_id, user_id="alice"
        )
        assert result_a.tenant_id == tenant_a
        assert result_b.tenant_id == tenant_b
        assert result_a.output_hash == result_b.output_hash == _sequential("project-alpha")
