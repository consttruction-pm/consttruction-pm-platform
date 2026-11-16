"""PostgreSQL twin coverage for the durable scheduling job lifecycle.

Set ``P6_TEST_POSTGRES_DSN`` to a reachable database; the tests create their own
schema and use unique tenants so they can run in parallel with other suites.
"""

import os
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from threading import Barrier, Thread

import pytest

from construction_pm.postgres_scheduling_job_lifecycle import (
    PostgresSchedulingJobRepository,
)
from construction_pm.scheduling_job_lifecycle import (
    SchedulingJobResult,
    SchedulingJobResultError,
    SchedulingJobService,
    SchedulingJobState,
)

pytestmark = pytest.mark.postgres

ENGINE = "cubi-26.0.0"


def _dsn() -> str:
    dsn = os.getenv("P6_TEST_POSTGRES_DSN") or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    if not dsn:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    return dsn


def _connection():
    psycopg = pytest.importorskip("psycopg")
    return psycopg.connect(_dsn(), autocommit=True)


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 16, 9, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now = self.now + timedelta(seconds=seconds)


def _request(tenant: str, **overrides):
    from construction_pm.scheduling_job_lifecycle import SchedulingJobRequest

    values = {
        "tenant_id": tenant,
        "project_id": "project-pg",
        "submitted_by": "alice",
        "request_fingerprint": "fingerprint-1",
        "engine_version": ENGINE,
        "calculation_identity": "calc-1",
        "max_attempts": 2,
    }
    values.update(overrides)
    return SchedulingJobRequest(**values)


def _result(job, output_hash="c" * 64):
    return SchedulingJobResult(
        tenant_id=job.tenant_id,
        project_id=job.project_id,
        job_id=job.job_id,
        engine_version=job.engine_version,
        calculation_identity=job.calculation_identity,
        output_hash=output_hash,
        payload={"project_finish": "2026-12-01", "floats": 3},
        persisted_at=datetime(2026, 11, 16, 9, 5, tzinfo=timezone.utc),
    )


def test_postgres_job_round_trip_and_result_persistence():
    tenant = f"p0f-{uuid.uuid4()}"
    clock = Clock()
    with _connection() as connection:
        repository = PostgresSchedulingJobRepository(connection)
        repository.initialize()
        service = SchedulingJobService(repository, clock=clock, lease_ttl=timedelta(seconds=60))
        try:
            submission = service.submit(_request(tenant))
            assert submission.deduplicated is False
            leased = service.claim(
                tenant_id=tenant, project_id="project-pg", job_id=submission.job.job_id,
                owner="worker-a",
            )
            done = service.complete(
                tenant_id=tenant,
                project_id="project-pg",
                job_id=submission.job.job_id,
                token=leased.lease_token,
                result=_result(submission.job),
            )
            assert done.state is SchedulingJobState.SUCCEEDED

            reloaded = service.get(
                tenant_id=tenant, project_id="project-pg",
                job_id=submission.job.job_id, user_id="alice",
            )
            assert reloaded.state is SchedulingJobState.SUCCEEDED
            stored = service.get_result(
                tenant_id=tenant, project_id="project-pg",
                job_id=submission.job.job_id, user_id="alice",
            )
            assert stored.output_hash == "c" * 64
            assert stored.payload == {"floats": 3, "project_finish": "2026-12-01"}

            # The partial unique index is gone once the job is terminal.
            again = service.submit(_request(tenant))
            assert again.deduplicated is False
            assert again.job.job_id != submission.job.job_id
        finally:
            connection.execute(
                "DELETE FROM scheduling_job_results WHERE tenant_id=%s", (tenant,)
            )
            connection.execute("DELETE FROM scheduling_jobs WHERE tenant_id=%s", (tenant,))


def test_postgres_single_flight_unique_index_rejects_a_second_active_job():
    tenant = f"p0f-{uuid.uuid4()}"
    clock = Clock()
    with _connection() as first, _connection() as second:
        first_repo = PostgresSchedulingJobRepository(first)
        second_repo = PostgresSchedulingJobRepository(second)
        first_repo.initialize()
        try:
            first_service = SchedulingJobService(first_repo, clock=clock)
            winner = first_service.submit(_request(tenant))
            assert winner.deduplicated is False

            second_service = SchedulingJobService(second_repo, clock=clock)
            loser = second_service.submit(_request(tenant))
            assert loser.deduplicated is True
            assert loser.job.job_id == winner.job.job_id
        finally:
            first.execute("DELETE FROM scheduling_jobs WHERE tenant_id=%s", (tenant,))


def test_postgres_compare_and_set_allows_only_one_winner():
    tenant = f"p0f-{uuid.uuid4()}"
    clock = Clock()
    with _connection() as first, _connection() as second:
        first_repo = PostgresSchedulingJobRepository(first)
        second_repo = PostgresSchedulingJobRepository(second)
        first_repo.initialize()
        try:
            submission = SchedulingJobService(first_repo, clock=clock).submit(_request(tenant))
            job_id = submission.job.job_id
            first_service = SchedulingJobService(first_repo, clock=clock)
            second_service = SchedulingJobService(second_repo, clock=clock)

            leased = first_service.claim(
                tenant_id=tenant, project_id="project-pg", job_id=job_id, owner="worker-a"
            )
            from construction_pm.scheduling_job_lifecycle import SchedulingJobLeaseError

            with pytest.raises(SchedulingJobLeaseError):
                second_service.renew(
                    tenant_id=tenant, project_id="project-pg",
                    job_id=job_id, token="not-the-token",
                )

            # Both workers hold the same stale revision; the database accepts one.
            stale_a = first_repo.get(tenant, "project-pg", job_id)
            stale_b = second_repo.get(tenant, "project-pg", job_id)
            assert stale_a is not None and stale_b is not None
            assert stale_a.revision == leased.revision

            next_revision = stale_a.revision + 1
            won = first_repo.compare_and_set(
                replace(stale_a, revision=next_revision, updated_at=clock.now),
                stale_a.revision,
            )
            lost = second_repo.compare_and_set(
                replace(stale_b, revision=next_revision, updated_at=clock.now),
                stale_b.revision,
            )
            assert won is True
            assert lost is False
        finally:
            first.execute("DELETE FROM scheduling_jobs WHERE tenant_id=%s", (tenant,))


def test_postgres_expired_lease_is_recovered_by_another_worker():
    tenant = f"p0f-{uuid.uuid4()}"
    clock = Clock()
    with _connection() as first, _connection() as second:
        first_repo = PostgresSchedulingJobRepository(first)
        second_repo = PostgresSchedulingJobRepository(second)
        first_repo.initialize()
        try:
            submission = SchedulingJobService(first_repo, clock=clock).submit(_request(tenant))
            job_id = submission.job.job_id
            service = SchedulingJobService(first_repo, clock=clock, lease_ttl=timedelta(seconds=30))
            service.claim(
                tenant_id=tenant, project_id="project-pg", job_id=job_id, owner="worker-a"
            )
            clock.advance(31)

            recovery = SchedulingJobService(second_repo, clock=clock)
            recovered = recovery.recover_expired()
            assert [job.state for job in recovered if job.job_id == job_id] == [
                SchedulingJobState.QUEUED
            ]
            reclaimed = recovery.claim(
                tenant_id=tenant, project_id="project-pg", job_id=job_id, owner="worker-b"
            )
            assert reclaimed.attempts == 2
            assert reclaimed.lease_owner == "worker-b"
        finally:
            first.execute("DELETE FROM scheduling_jobs WHERE tenant_id=%s", (tenant,))


def test_postgres_result_is_immutable_per_job():
    tenant = f"p0f-{uuid.uuid4()}"
    clock = Clock()
    with _connection() as connection:
        repository = PostgresSchedulingJobRepository(connection)
        repository.initialize()
        service = SchedulingJobService(repository, clock=clock)
        try:
            submission = service.submit(_request(tenant))
            leased = service.claim(
                tenant_id=tenant, project_id="project-pg",
                job_id=submission.job.job_id, owner="worker-a",
            )
            service.complete(
                tenant_id=tenant,
                project_id="project-pg",
                job_id=submission.job.job_id,
                token=leased.lease_token,
                result=_result(submission.job),
            )
            # Identical replay is tolerated, a different result is rejected.
            repository.put_result(_result(submission.job))
            with pytest.raises(SchedulingJobResultError):
                repository.put_result(_result(submission.job, output_hash="d" * 64))
        finally:
            connection.execute(
                "DELETE FROM scheduling_job_results WHERE tenant_id=%s", (tenant,)
            )
            connection.execute("DELETE FROM scheduling_jobs WHERE tenant_id=%s", (tenant,))


def test_postgres_concurrent_submissions_create_one_active_job():
    tenant = f"p0f-{uuid.uuid4()}"
    clock = Clock()
    barrier = Barrier(6)
    outcomes: list[tuple[str, bool]] = []
    errors: list[Exception] = []

    def worker() -> None:
        try:
            with _connection() as connection:
                repository = PostgresSchedulingJobRepository(connection)
                repository.initialize()
                service = SchedulingJobService(repository, clock=clock)
                barrier.wait()
                submission = service.submit(_request(tenant))
                outcomes.append((submission.job.job_id, submission.deduplicated))
        except Exception as error:  # pragma: no cover - asserted below
            errors.append(error)

    threads = [Thread(target=worker) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    try:
        assert errors == []
        assert len({job_id for job_id, _ in outcomes}) == 1
        assert sum(1 for _, deduplicated in outcomes if not deduplicated) == 1
    finally:
        with _connection() as connection:
            connection.execute("DELETE FROM scheduling_jobs WHERE tenant_id=%s", (tenant,))


def test_postgres_executor_drains_a_real_queue():
    from construction_pm.scheduling_execution_budget import GlobalExecutionBudget
    from construction_pm.scheduling_job_executor import SchedulingJobExecutor

    tenant = f"p0g-{uuid.uuid4()}"
    with _connection() as connection:
        repository = PostgresSchedulingJobRepository(connection)
        repository.initialize()
        service = SchedulingJobService(repository, lease_ttl=timedelta(seconds=60))
        job_ids = [
            service.submit(
                _request(tenant, request_fingerprint=f"executor-{index}")
            ).job.job_id
            for index in range(3)
        ]
        try:
            executor = SchedulingJobExecutor(
                service,
                calculate=lambda job: _result(job),
                owner="pg-worker",
                budget=GlobalExecutionBudget(2),
                poll_interval=0.01,
            )
            summary = executor.run_until_idle(timeout=60)

            assert summary.succeeded == 3
            assert repository.count_pending(tenant_id=tenant) == 0
            for job_id in job_ids:
                stored = service.get_result(
                    tenant_id=tenant,
                    project_id="project-pg",
                    job_id=job_id,
                    user_id="alice",
                )
                assert stored.output_hash == "c" * 64
        finally:
            connection.execute(
                "DELETE FROM scheduling_job_results WHERE tenant_id=%s", (tenant,)
            )
            connection.execute(
                "DELETE FROM scheduling_jobs WHERE tenant_id=%s", (tenant,)
            )
