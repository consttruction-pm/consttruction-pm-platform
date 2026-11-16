"""P0-F lifecycle tests over the reference in-memory repository."""

from datetime import datetime, timedelta, timezone
from threading import Barrier, Thread

import pytest

from construction_pm.scheduling_job_lifecycle import (
    InMemorySchedulingJobRepository,
    SchedulingJobCancelled,
    SchedulingJobError,
    SchedulingJobIdentityMismatch,
    SchedulingJobLeaseError,
    SchedulingJobNotFound,
    SchedulingJobRequest,
    SchedulingJobResult,
    SchedulingJobResultError,
    SchedulingJobService,
    SchedulingJobState,
    SchedulingJobStateError,
    stable_job_id,
)

TENANT = "tenant-p0f"
PROJECT = "project-p0f"
ENGINE = "cubi-26.0.0"
IDENTITY = "calc-identity-1"


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 16, 9, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now = self.now + timedelta(seconds=seconds)


def _service(**kwargs):
    clock = kwargs.pop("clock", None) or Clock()
    repository = kwargs.pop("repository", None) or InMemorySchedulingJobRepository()
    service = SchedulingJobService(repository, clock=clock, **kwargs)
    return service, repository, clock


def _request(**overrides) -> SchedulingJobRequest:
    values = {
        "tenant_id": TENANT,
        "project_id": PROJECT,
        "submitted_by": "alice",
        "request_fingerprint": "fingerprint-1",
        "engine_version": ENGINE,
        "calculation_identity": IDENTITY,
    }
    values.update(overrides)
    return SchedulingJobRequest(**values)


def _result(job, output_hash="a" * 64, **overrides) -> SchedulingJobResult:
    values = {
        "tenant_id": job.tenant_id,
        "project_id": job.project_id,
        "job_id": job.job_id,
        "engine_version": job.engine_version,
        "calculation_identity": job.calculation_identity,
        "output_hash": output_hash,
        "payload": {"project_finish": "2026-12-01"},
        "persisted_at": datetime(2026, 11, 16, 9, 5, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return SchedulingJobResult(**values)


class PerUserScope:
    """De-duplication only inside one user's own authorization scope."""

    def dedup_scope(self, *, tenant_id, project_id, user_id) -> str:
        return f"{tenant_id}:{project_id}:{user_id}"

    def can_view(self, *, tenant_id, project_id, user_id, job) -> bool:
        return job.submitted_by == user_id and job.dedup_scope.endswith(f":{user_id}")


def test_submit_is_single_flight_and_deterministic():
    service, repository, _clock = _service()
    first = service.submit(_request())
    second = service.submit(_request(submitted_by="bob"))

    assert first.deduplicated is False
    assert second.deduplicated is True
    assert second.job.job_id == first.job.job_id
    assert first.job.state is SchedulingJobState.QUEUED
    assert first.job.job_id == stable_job_id(first.job.key, 0)
    assert repository.count_for_key(first.job.key) == 1


def test_single_flight_is_scoped_by_authorization():
    service, _repository, _clock = _service(authorization=PerUserScope())
    alice = service.submit(_request(submitted_by="alice"))
    bob = service.submit(_request(submitted_by="bob"))

    assert alice.job.job_id != bob.job.job_id
    assert alice.deduplicated is False
    assert bob.deduplicated is False
    with pytest.raises(SchedulingJobNotFound):
        service.get(
            tenant_id=TENANT, project_id=PROJECT, job_id=alice.job.job_id, user_id="bob"
        )


def test_claim_then_second_claim_is_rejected_and_renew_extends_the_lease():
    service, _repository, clock = _service(lease_ttl=timedelta(seconds=60))
    job = service.submit(_request()).job

    leased = service.claim(
        tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, owner="worker-a"
    )
    assert leased.state is SchedulingJobState.LEASED
    assert leased.attempts == 1
    assert leased.lease_token
    with pytest.raises(SchedulingJobLeaseError):
        service.claim(
            tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, owner="worker-b"
        )

    clock.advance(30)
    renewed = service.renew(
        tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, token=leased.lease_token
    )
    assert renewed.lease_expires_at == clock.now + timedelta(seconds=60)
    assert renewed.revision > leased.revision


def test_complete_persists_the_canonical_result_once():
    service, repository, _clock = _service()
    job = service.submit(_request()).job
    leased = service.claim(
        tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, owner="worker-a"
    )

    done = service.complete(
        tenant_id=TENANT,
        project_id=PROJECT,
        job_id=job.job_id,
        token=leased.lease_token,
        result=_result(job),
    )
    assert done.state is SchedulingJobState.SUCCEEDED
    assert done.lease_token is None
    stored = service.get_result(
        tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, user_id="alice"
    )
    assert stored.output_hash == "a" * 64
    assert stored.payload == {"project_finish": "2026-12-01"}

    # An identical replay is accepted, a different result is not.
    repository.put_result(_result(done))
    with pytest.raises(SchedulingJobResultError):
        repository.put_result(_result(done, output_hash="b" * 64))
    with pytest.raises(SchedulingJobLeaseError):
        service.complete(
            tenant_id=TENANT,
            project_id=PROJECT,
            job_id=job.job_id,
            token=leased.lease_token,
            result=_result(job),
        )


def test_complete_rejects_a_different_engine_identity_and_keeps_the_lease():
    service, _repository, _clock = _service()
    job = service.submit(_request()).job
    leased = service.claim(
        tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, owner="worker-a"
    )

    with pytest.raises(SchedulingJobIdentityMismatch):
        service.complete(
            tenant_id=TENANT,
            project_id=PROJECT,
            job_id=job.job_id,
            token=leased.lease_token,
            result=_result(job, engine_version="cubi-26.0.1"),
        )
    still_leased = service.get(
        tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, user_id="alice"
    )
    assert still_leased.state is SchedulingJobState.LEASED
    with pytest.raises(SchedulingJobResultError):
        service.get_result(
            tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, user_id="alice"
        )


def test_retryable_failure_requeues_until_max_attempts_then_fails():
    service, _repository, _clock = _service()
    job = service.submit(_request(max_attempts=2)).job

    for attempt in (1, 2):
        leased = service.claim(
            tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, owner="worker-a"
        )
        assert leased.attempts == attempt
        failed = service.fail(
            tenant_id=TENANT,
            project_id=PROJECT,
            job_id=job.job_id,
            token=leased.lease_token,
            error="ENGINE_TIMEOUT",
            retryable=True,
        )
        if attempt == 1:
            assert failed.state is SchedulingJobState.QUEUED
            assert failed.last_error == "ENGINE_TIMEOUT"
        else:
            assert failed.state is SchedulingJobState.FAILED
    with pytest.raises(SchedulingJobStateError):
        service.claim(
            tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, owner="worker-b"
        )


def test_non_retryable_failure_is_terminal():
    service, _repository, _clock = _service()
    job = service.submit(_request()).job
    leased = service.claim(
        tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, owner="worker-a"
    )
    failed = service.fail(
        tenant_id=TENANT,
        project_id=PROJECT,
        job_id=job.job_id,
        token=leased.lease_token,
        error="INVALID_INPUT",
        retryable=False,
    )
    assert failed.state is SchedulingJobState.FAILED
    with pytest.raises(SchedulingJobResultError):
        service.get_result(
            tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, user_id="alice"
        )


def test_cancel_queued_job_is_terminal():
    service, _repository, _clock = _service()
    job = service.submit(_request()).job
    cancelled = service.cancel(
        tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, user_id="alice"
    )
    assert cancelled.state is SchedulingJobState.CANCELLED
    assert cancelled.cancel_requested_by == "alice"


def test_cancel_leased_job_is_cooperative_and_never_publishes_a_result():
    service, _repository, _clock = _service()
    job = service.submit(_request()).job
    leased = service.claim(
        tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, owner="worker-a"
    )
    requested = service.cancel(
        tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, user_id="alice"
    )
    assert requested.state is SchedulingJobState.LEASED
    assert requested.cancel_requested is True

    with pytest.raises(SchedulingJobCancelled):
        service.checkpoint(
            tenant_id=TENANT,
            project_id=PROJECT,
            job_id=job.job_id,
            token=leased.lease_token,
        )
    final = service.get(
        tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, user_id="alice"
    )
    assert final.state is SchedulingJobState.CANCELLED
    with pytest.raises(SchedulingJobResultError):
        service.get_result(
            tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, user_id="alice"
        )
    # The stale lease token cannot complete a cancelled job.
    with pytest.raises(SchedulingJobLeaseError):
        service.complete(
            tenant_id=TENANT,
            project_id=PROJECT,
            job_id=job.job_id,
            token=leased.lease_token,
            result=_result(job),
        )


def test_expired_lease_is_recovered_and_reclaimable():
    service, _repository, clock = _service(lease_ttl=timedelta(seconds=30))
    job = service.submit(_request()).job
    service.claim(tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, owner="worker-a")
    clock.advance(31)

    recovered = service.recover_expired()
    assert [item.state for item in recovered] == [SchedulingJobState.QUEUED]
    assert recovered[0].last_error == "LEASE_EXPIRED"

    second = service.claim(
        tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, owner="worker-b"
    )
    assert second.attempts == 2
    assert second.lease_owner == "worker-b"


def test_expired_lease_with_exhausted_attempts_fails():
    service, _repository, clock = _service(lease_ttl=timedelta(seconds=30))
    job = service.submit(_request(max_attempts=1)).job
    service.claim(tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, owner="worker-a")
    clock.advance(31)

    recovered = service.recover_expired()
    assert [item.state for item in recovered] == [SchedulingJobState.FAILED]
    assert recovered[0].last_error == "LEASE_EXPIRED"


def test_expired_lease_with_cancellation_request_is_cancelled():
    service, _repository, clock = _service(lease_ttl=timedelta(seconds=30))
    job = service.submit(_request()).job
    service.claim(tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, owner="worker-a")
    service.cancel(tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, user_id="alice")
    clock.advance(31)

    recovered = service.recover_expired()
    assert [item.state for item in recovered] == [SchedulingJobState.CANCELLED]


def test_terminal_job_allows_a_new_generation():
    service, repository, _clock = _service()
    first = service.submit(_request()).job
    cancelled = service.cancel(
        tenant_id=TENANT, project_id=PROJECT, job_id=first.job_id, user_id="alice"
    )
    assert cancelled.state is SchedulingJobState.CANCELLED

    second = service.submit(_request())
    assert second.deduplicated is False
    assert second.job.job_id != first.job_id
    assert second.job.job_id == stable_job_id(first.key, 1)
    assert repository.count_for_key(first.key) == 2


def test_concurrent_submissions_create_exactly_one_active_job():
    service, repository, _clock = _service()
    barrier = Barrier(8)
    job_ids: list[str] = []
    deduplicated: list[bool] = []
    errors: list[Exception] = []

    def worker() -> None:
        try:
            barrier.wait()
            submission = service.submit(_request())
            job_ids.append(submission.job.job_id)
            deduplicated.append(submission.deduplicated)
        except Exception as error:  # pragma: no cover - asserted below
            errors.append(error)

    threads = [Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(set(job_ids)) == 1
    assert deduplicated.count(False) == 1
    assert repository.count_for_key(service.submit(_request()).job.key) == 1


def test_invalid_inputs_are_rejected():
    with pytest.raises(SchedulingJobError):
        _request(engine_version="  ")
    with pytest.raises(SchedulingJobError):
        _request(max_attempts=0)
    with pytest.raises(SchedulingJobError):
        SchedulingJobService(InMemorySchedulingJobRepository(), lease_ttl=timedelta(0))
    service, _repository, _clock = _service()
    with pytest.raises(SchedulingJobNotFound):
        service.get(tenant_id=TENANT, project_id=PROJECT, job_id="missing", user_id="alice")


def test_job_persists_the_authoritative_engine_hash():
    """The lifecycle wraps the single engine; it never calculates on its own."""
    from construction_pm.scheduling.benchmark_fixtures import (
        canonical_hash,
        date_network,
        date_schedule_payload,
        run_date_schedule,
    )

    fixture = date_network(50, "dag")
    direct = run_date_schedule(fixture)
    expected_hash = canonical_hash(date_schedule_payload(direct))

    service, _repository, _clock = _service()
    job = service.submit(
        _request(request_fingerprint="dag-50", calculation_identity="fixture-dag-50")
    ).job
    leased = service.claim(
        tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, owner="worker-a"
    )
    service.complete(
        tenant_id=TENANT,
        project_id=PROJECT,
        job_id=job.job_id,
        token=leased.lease_token,
        result=_result(
            job,
            output_hash=expected_hash,
            payload={"project_finish": direct.project_finish.isoformat(), "activities": len(direct.activities)},
        ),
    )

    stored = service.get_result(
        tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, user_id="alice"
    )
    assert stored.output_hash == expected_hash
    assert stored.payload["activities"] == 50
