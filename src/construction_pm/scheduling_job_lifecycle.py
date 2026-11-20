"""P0-F: durable Scheduling Job lifecycle around the authoritative scheduler.

A scheduling run is expensive and must survive process loss, duplicate
submission, cancellation and retries without ever calculating a second,
different result. This module defines the job identity, the lease-based
execution protocol, retry and cancellation rules, result persistence and
single-flight de-duplication. It does not calculate anything: the caller runs
``construction_pm.scheduling`` and persists the canonical result hash.

Design rules
------------
* One authoritative engine identity. A job records ``engine_version`` and the
  scheduling ``calculation_identity``; a completion whose identity differs is
  rejected, so a retry on another engine cannot publish a mixed result.
* Leases, not locks. Only the lease holder may complete, renew or report a
  failure, and an expired lease can be taken over by another worker after an
  explicit expiry check.
* Every mutation is a compare-and-set on the stored job revision, so the same
  service works over an in-memory repository and over PostgreSQL row updates
  without duplicating transition rules in SQL.
* Single-flight de-duplication is scoped by an authorization boundary supplied
  by the caller. Two callers in different scopes never see, reuse or learn about
  each other's job, and ``can_view`` is re-checked before any job is returned.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from threading import RLock
from typing import Callable, Mapping, Protocol


class SchedulingJobState(str, Enum):
    QUEUED = "QUEUED"
    LEASED = "LEASED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_JOB_STATES = frozenset({
    SchedulingJobState.SUCCEEDED,
    SchedulingJobState.FAILED,
    SchedulingJobState.CANCELLED,
})


class SchedulingJobError(ValueError):
    pass


class SchedulingJobNotFound(SchedulingJobError):
    pass


class SchedulingJobLeaseError(SchedulingJobError):
    """The caller does not hold a live lease for this job."""


class SchedulingJobStateError(SchedulingJobError):
    """The requested transition is not valid for the current state."""


class SchedulingJobIdentityMismatch(SchedulingJobError):
    """The completion came from a different engine or calculation identity."""


class SchedulingJobCancelled(SchedulingJobLeaseError):
    """Cooperative cancellation observed at a checkpoint."""


class SchedulingJobResultError(SchedulingJobError):
    pass


def _require_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchedulingJobError(f"INVALID_{name.upper()}")
    return value


def _require_aware(name: str, value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise SchedulingJobError(f"INVALID_{name.upper()}")
    return value


@dataclass(frozen=True)
class SchedulingJobRequest:
    """Immutable input identity for one scheduling run."""

    tenant_id: str
    project_id: str
    submitted_by: str
    request_fingerprint: str
    engine_version: str
    calculation_identity: str
    max_attempts: int = 3

    def __post_init__(self) -> None:
        for name in (
            "tenant_id",
            "project_id",
            "submitted_by",
            "request_fingerprint",
            "engine_version",
            "calculation_identity",
        ):
            _require_text(name, getattr(self, name))
        if (
            isinstance(self.max_attempts, bool)
            or not isinstance(self.max_attempts, int)
            or self.max_attempts < 1
        ):
            raise SchedulingJobError("INVALID_MAX_ATTEMPTS")


@dataclass(frozen=True)
class SchedulingJob:
    tenant_id: str
    project_id: str
    job_id: str
    dedup_scope: str
    request_fingerprint: str
    submitted_by: str
    state: SchedulingJobState
    attempts: int
    max_attempts: int
    engine_version: str
    calculation_identity: str
    created_at: datetime
    updated_at: datetime
    lease_owner: str | None = None
    lease_token: str | None = None
    lease_expires_at: datetime | None = None
    cancel_requested: bool = False
    cancel_requested_by: str | None = None
    last_error: str | None = None
    revision: int = 0
    # Immutable run parameters are part of the submission identity: the worker
    # needs the exact snapshot revision a caller asked for, and it must survive
    # a worker restart. Stored as ordered string pairs so the job stays
    # hashable and the persistence adapters need no nested-JSON contract.
    run_parameters: tuple[tuple[str, str], ...] = ()

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_JOB_STATES

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (
            self.tenant_id,
            self.project_id,
            self.dedup_scope,
            self.request_fingerprint,
        )

    def lease_is_live(self, now: datetime) -> bool:
        return (
            self.state is SchedulingJobState.LEASED
            and self.lease_expires_at is not None
            and self.lease_expires_at > now
        )

    def validate(self) -> None:
        for name in (
            "tenant_id",
            "project_id",
            "job_id",
            "dedup_scope",
            "request_fingerprint",
            "submitted_by",
            "engine_version",
            "calculation_identity",
        ):
            _require_text(name, getattr(self, name))
        if not isinstance(self.state, SchedulingJobState):
            raise SchedulingJobError("INVALID_JOB_STATE")
        for name in ("attempts", "max_attempts", "revision"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise SchedulingJobError(f"INVALID_JOB_{name.upper()}")
        if not 0 <= self.attempts <= self.max_attempts:
            raise SchedulingJobError("INVALID_JOB_ATTEMPTS")
        _require_aware("created_at", self.created_at)
        _require_aware("updated_at", self.updated_at)
        if self.state is SchedulingJobState.LEASED:
            _require_text("lease_owner", self.lease_owner)
            _require_text("lease_token", self.lease_token)
            _require_aware("lease_expires_at", self.lease_expires_at)
        elif self.lease_owner or self.lease_token or self.lease_expires_at:
            raise SchedulingJobError("LEASE_PRESENT_ON_NON_LEASED_JOB")
        if not isinstance(self.run_parameters, tuple):
            raise SchedulingJobError("INVALID_JOB_RUN_PARAMETERS")
        seen: set[str] = set()
        for item in self.run_parameters:
            if not isinstance(item, tuple) or len(item) != 2:
                raise SchedulingJobError("INVALID_JOB_RUN_PARAMETERS")
            name, value = item
            if not isinstance(name, str) or not name.strip() or not isinstance(value, str):
                raise SchedulingJobError("INVALID_JOB_RUN_PARAMETERS")
            if name in seen:
                raise SchedulingJobError("DUPLICATE_JOB_RUN_PARAMETER")
            seen.add(name)

    def run_parameter_map(self) -> dict[str, str]:
        return dict(self.run_parameters)


@dataclass(frozen=True)
class SchedulingJobResult:
    tenant_id: str
    project_id: str
    job_id: str
    engine_version: str
    calculation_identity: str
    output_hash: str
    payload: Mapping[str, object]
    persisted_at: datetime

    def __post_init__(self) -> None:
        for name in (
            "tenant_id",
            "project_id",
            "job_id",
            "engine_version",
            "calculation_identity",
            "output_hash",
        ):
            _require_text(name, getattr(self, name))
        _require_aware("persisted_at", self.persisted_at)
        if not isinstance(self.payload, Mapping):
            raise SchedulingJobResultError("INVALID_RESULT_PAYLOAD")

    def canonical_payload_json(self) -> str:
        return json.dumps(
            dict(self.payload),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )


class SchedulingJobAuthorization(Protocol):
    """Authorization boundary for de-duplication and result visibility."""

    def dedup_scope(self, *, tenant_id: str, project_id: str, user_id: str) -> str: ...

    def can_view(
        self, *, tenant_id: str, project_id: str, user_id: str, job: SchedulingJob
    ) -> bool: ...


class ProjectScopeAuthorization:
    """Default boundary: the tenant/project pair is the de-duplication scope.

    Deployments that model project membership replace this with a policy that
    returns a membership-derived scope and checks the caller's project access.
    """

    def dedup_scope(self, *, tenant_id: str, project_id: str, user_id: str) -> str:
        return f"{tenant_id}:{project_id}"

    def can_view(
        self, *, tenant_id: str, project_id: str, user_id: str, job: SchedulingJob
    ) -> bool:
        return job.tenant_id == tenant_id and job.project_id == project_id


class SchedulingJobRepository(Protocol):
    """Persistence boundary. Every mutation is a revision compare-and-set."""

    def get(self, tenant_id: str, project_id: str, job_id: str) -> SchedulingJob | None: ...

    def find_active(self, key: tuple[str, str, str, str]) -> SchedulingJob | None: ...

    def count_for_key(self, key: tuple[str, str, str, str]) -> int: ...

    def create(self, job: SchedulingJob) -> bool: ...

    def compare_and_set(self, job: SchedulingJob, expected_revision: int) -> bool: ...

    def put_result(self, result: SchedulingJobResult) -> None: ...

    def get_result(
        self, tenant_id: str, project_id: str, job_id: str
    ) -> SchedulingJobResult | None: ...

    def find_expired_leases(
        self, now: datetime, *, limit: int
    ) -> tuple[SchedulingJob, ...]: ...

    def find_queued(
        self,
        limit: int,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> tuple[SchedulingJob, ...]: ...

    def count_pending(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> int: ...


class InMemorySchedulingJobRepository:
    """Reference repository with the same revision semantics as the SQL one."""

    def __init__(self) -> None:
        self._jobs: dict[tuple[str, str, str], SchedulingJob] = {}
        self._results: dict[tuple[str, str, str], SchedulingJobResult] = {}
        self._lock = RLock()

    def get(self, tenant_id: str, project_id: str, job_id: str) -> SchedulingJob | None:
        with self._lock:
            return self._jobs.get((tenant_id, project_id, job_id))

    def find_active(self, key: tuple[str, str, str, str]) -> SchedulingJob | None:
        with self._lock:
            matches = [
                job
                for job in self._jobs.values()
                if job.key == key and not job.is_terminal
            ]
        if len(matches) > 1:
            raise SchedulingJobError("MULTIPLE_ACTIVE_JOBS_FOR_KEY")
        return matches[0] if matches else None

    def count_for_key(self, key: tuple[str, str, str, str]) -> int:
        with self._lock:
            return sum(1 for job in self._jobs.values() if job.key == key)

    def create(self, job: SchedulingJob) -> bool:
        job.validate()
        with self._lock:
            job_key = (job.tenant_id, job.project_id, job.job_id)
            if job_key in self._jobs:
                return False
            active = [
                existing
                for existing in self._jobs.values()
                if existing.key == job.key and not existing.is_terminal
            ]
            if active and not job.is_terminal:
                return False
            self._jobs[job_key] = job
            return True

    def compare_and_set(self, job: SchedulingJob, expected_revision: int) -> bool:
        job.validate()
        with self._lock:
            job_key = (job.tenant_id, job.project_id, job.job_id)
            current = self._jobs.get(job_key)
            if current is None or current.revision != expected_revision:
                return False
            self._jobs[job_key] = job
            return True

    def put_result(self, result: SchedulingJobResult) -> None:
        with self._lock:
            key = (result.tenant_id, result.project_id, result.job_id)
            existing = self._results.get(key)
            if existing is not None:
                if (
                    existing.output_hash == result.output_hash
                    and existing.engine_version == result.engine_version
                    and existing.calculation_identity == result.calculation_identity
                ):
                    # Idempotent replay of an identical completion.
                    return
                raise SchedulingJobResultError("RESULT_ALREADY_PERSISTED")
            self._results[key] = result

    def get_result(
        self, tenant_id: str, project_id: str, job_id: str
    ) -> SchedulingJobResult | None:
        with self._lock:
            return self._results.get((tenant_id, project_id, job_id))

    def find_expired_leases(
        self, now: datetime, *, limit: int
    ) -> tuple[SchedulingJob, ...]:
        with self._lock:
            expired = [
                job
                for job in self._jobs.values()
                if job.state is SchedulingJobState.LEASED
                and job.lease_expires_at is not None
                and job.lease_expires_at <= now
            ]
        expired.sort(key=lambda job: (job.lease_expires_at, job.job_id))
        return tuple(expired[:limit])

    def find_queued(
        self,
        limit: int,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> tuple[SchedulingJob, ...]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise SchedulingJobError("INVALID_QUEUE_LIMIT")
        with self._lock:
            queued = [
                job
                for job in self._jobs.values()
                if job.state is SchedulingJobState.QUEUED
                and (tenant_id is None or job.tenant_id == tenant_id)
                and (project_id is None or job.project_id == project_id)
            ]
        queued.sort(key=lambda job: (job.created_at, job.job_id))
        return tuple(queued[:limit])

    def count_pending(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> int:
        with self._lock:
            return sum(
                1
                for job in self._jobs.values()
                if job.state is SchedulingJobState.QUEUED
                and (tenant_id is None or job.tenant_id == tenant_id)
                and (project_id is None or job.project_id == project_id)
            )


@dataclass(frozen=True)
class SchedulingJobSubmission:
    job: SchedulingJob
    deduplicated: bool


def stable_job_id(key: tuple[str, str, str, str], generation: int) -> str:
    """Deterministic job identity for one single-flight generation."""
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
        raise SchedulingJobError("INVALID_JOB_GENERATION")
    material = json.dumps(
        {"key": list(key), "generation": generation},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def new_lease_token(job_id: str, attempt: int, owner: str, now: datetime) -> str:
    material = f"{job_id}|{attempt}|{owner}|{now.isoformat()}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class SchedulingJobService:
    """Lease-based lifecycle for authoritative scheduling runs."""

    _CAS_RETRIES = 8

    def __init__(
        self,
        repository: SchedulingJobRepository,
        *,
        authorization: SchedulingJobAuthorization | None = None,
        clock: Callable[[], datetime] | None = None,
        lease_ttl: timedelta = timedelta(seconds=120),
    ) -> None:
        if not isinstance(lease_ttl, timedelta) or lease_ttl <= timedelta(0):
            raise SchedulingJobError("INVALID_LEASE_TTL")
        self._repository = repository
        self._authorization = authorization or ProjectScopeAuthorization()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._lease_ttl = lease_ttl

    # -- submission -------------------------------------------------------

    def submit(
        self,
        request: SchedulingJobRequest,
        *,
        run_parameters: tuple[tuple[str, str], ...] = (),
    ) -> SchedulingJobSubmission:
        if not isinstance(run_parameters, tuple):
            raise SchedulingJobError("INVALID_JOB_RUN_PARAMETERS")
        # Canonical order keeps the persisted form and every in-flight compare
        # independent of the caller's argument order.
        run_parameters = tuple(sorted(run_parameters))
        scope = self._authorization.dedup_scope(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            user_id=request.submitted_by,
        )
        key = (
            request.tenant_id,
            request.project_id,
            scope,
            request.request_fingerprint,
        )
        active = self._repository.find_active(key)
        if active is not None:
            if not self._authorization.can_view(
                tenant_id=request.tenant_id,
                project_id=request.project_id,
                user_id=request.submitted_by,
                job=active,
            ):
                # De-duplication must never expose another caller's run. The
                # scope is part of the key, so this is a defensive check.
                raise SchedulingJobError("SCHEDULING_JOB_NOT_VISIBLE")
            if active.run_parameters != run_parameters:
                # The fingerprint promises one immutable input identity. A
                # different parameter set under the same fingerprint would run
                # a different calculation than the caller asked for.
                raise SchedulingJobError("SCHEDULING_JOB_PARAMETER_CONFLICT")
            return SchedulingJobSubmission(active, deduplicated=True)

        now = self._clock()
        for _ in range(self._CAS_RETRIES):
            generation = self._repository.count_for_key(key)
            job_id = stable_job_id(key, generation)
            job = SchedulingJob(
                tenant_id=request.tenant_id,
                project_id=request.project_id,
                job_id=job_id,
                dedup_scope=scope,
                request_fingerprint=request.request_fingerprint,
                submitted_by=request.submitted_by,
                state=SchedulingJobState.QUEUED,
                attempts=0,
                max_attempts=request.max_attempts,
                engine_version=request.engine_version,
                calculation_identity=request.calculation_identity,
                created_at=now,
                updated_at=now,
                run_parameters=run_parameters,
            )
            if self._repository.create(job):
                return SchedulingJobSubmission(job, deduplicated=False)
            # Another worker won the single-flight or identity race.
            existing = self._repository.find_active(key)
            if existing is None:
                continue
            if not self._authorization.can_view(
                tenant_id=request.tenant_id,
                project_id=request.project_id,
                user_id=request.submitted_by,
                job=existing,
            ):
                raise SchedulingJobError("SCHEDULING_JOB_NOT_VISIBLE")
            return SchedulingJobSubmission(existing, deduplicated=True)
        raise SchedulingJobError("SCHEDULING_JOB_SUBMIT_CONTENTION")

    # -- reading ----------------------------------------------------------

    def get(
        self, *, tenant_id: str, project_id: str, job_id: str, user_id: str
    ) -> SchedulingJob:
        job = self._load(tenant_id, project_id, job_id)
        if not self._authorization.can_view(
            tenant_id=tenant_id,
            project_id=project_id,
            user_id=user_id,
            job=job,
        ):
            raise SchedulingJobNotFound("SCHEDULING_JOB_NOT_FOUND")
        return job

    def get_result(
        self, *, tenant_id: str, project_id: str, job_id: str, user_id: str
    ) -> SchedulingJobResult:
        job = self.get(
            tenant_id=tenant_id, project_id=project_id, job_id=job_id, user_id=user_id
        )
        if job.state is not SchedulingJobState.SUCCEEDED:
            raise SchedulingJobResultError("SCHEDULING_JOB_NOT_SUCCEEDED")
        result = self._repository.get_result(tenant_id, project_id, job_id)
        if result is None:
            raise SchedulingJobResultError("SCHEDULING_JOB_RESULT_MISSING")
        if (
            result.engine_version != job.engine_version
            or result.calculation_identity != job.calculation_identity
        ):
            raise SchedulingJobIdentityMismatch("SCHEDULING_JOB_RESULT_IDENTITY_MISMATCH")
        return result

    # -- worker queue -----------------------------------------------------

    def queued_jobs(
        self,
        limit: int,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> tuple[SchedulingJob, ...]:
        """Discover queued jobs for a trusted worker.

        Discovery is not user-facing: it returns candidates that a worker then
        claims, and claim/complete still require the lease token. Authorization
        is enforced on ``submit``, ``get``, ``get_result`` and ``cancel``, so a
        worker never becomes a way to read another user's run.
        """
        return self._repository.find_queued(
            limit, tenant_id=tenant_id, project_id=project_id
        )

    def pending_count(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> int:
        return self._repository.count_pending(
            tenant_id=tenant_id, project_id=project_id
        )

    @property
    def lease_ttl(self) -> timedelta:
        return self._lease_ttl

    # -- leases -----------------------------------------------------------

    def claim(
        self, *, tenant_id: str, project_id: str, job_id: str, owner: str
    ) -> SchedulingJob:
        _require_text("owner", owner)
        for _ in range(self._CAS_RETRIES):
            now = self._clock()
            job = self._load(tenant_id, project_id, job_id)
            if job.is_terminal:
                raise SchedulingJobStateError("SCHEDULING_JOB_TERMINAL")
            if job.state is SchedulingJobState.LEASED:
                if job.lease_expires_at is not None and job.lease_expires_at > now:
                    raise SchedulingJobLeaseError("SCHEDULING_JOB_LEASE_HELD")
                if job.cancel_requested:
                    self._cancel_leased(job, now)
                    raise SchedulingJobStateError("SCHEDULING_JOB_CANCELLED")
                if job.attempts >= job.max_attempts:
                    self._fail_leased(job, now, "LEASE_EXPIRED")
                    raise SchedulingJobStateError("SCHEDULING_JOB_ATTEMPTS_EXHAUSTED")
            attempt = job.attempts + 1
            leased = replace(
                job,
                state=SchedulingJobState.LEASED,
                attempts=attempt,
                lease_owner=owner,
                lease_token=new_lease_token(job.job_id, attempt, owner, now),
                lease_expires_at=now + self._lease_ttl,
                updated_at=now,
                revision=job.revision + 1,
            )
            if self._repository.compare_and_set(leased, job.revision):
                return leased
        raise SchedulingJobError("SCHEDULING_JOB_LEASE_CONTENTION")

    def renew(
        self, *, tenant_id: str, project_id: str, job_id: str, token: str
    ) -> SchedulingJob:
        for _ in range(self._CAS_RETRIES):
            now = self._clock()
            job = self._load(tenant_id, project_id, job_id)
            self._require_lease(job, token, now)
            if job.cancel_requested:
                # Renewal is one of the documented cancellation observation
                # points, so persist the terminal state instead of only raising.
                self._cancel_leased(job, now)
                raise SchedulingJobCancelled("SCHEDULING_JOB_CANCEL_REQUESTED")
            renewed = replace(
                job,
                lease_expires_at=now + self._lease_ttl,
                updated_at=now,
                revision=job.revision + 1,
            )
            if self._repository.compare_and_set(renewed, job.revision):
                return renewed
        raise SchedulingJobError("SCHEDULING_JOB_LEASE_CONTENTION")

    def checkpoint(
        self, *, tenant_id: str, project_id: str, job_id: str, token: str
    ) -> SchedulingJob:
        """Cooperative cancellation check between calculation slices."""
        for _ in range(self._CAS_RETRIES):
            now = self._clock()
            job = self._load(tenant_id, project_id, job_id)
            if job.cancel_requested:
                self._cancel_leased(job, now)
                raise SchedulingJobCancelled("SCHEDULING_JOB_CANCELLED") from None
            self._require_lease(job, token, now)
            return job
        raise SchedulingJobError("SCHEDULING_JOB_LEASE_CONTENTION")

    def complete(
        self,
        *,
        tenant_id: str,
        project_id: str,
        job_id: str,
        token: str,
        result: SchedulingJobResult,
    ) -> SchedulingJob:
        if (
            result.tenant_id != tenant_id
            or result.project_id != project_id
            or result.job_id != job_id
        ):
            raise SchedulingJobIdentityMismatch("SCHEDULING_JOB_RESULT_IDENTITY_MISMATCH")
        for _ in range(self._CAS_RETRIES):
            now = self._clock()
            job = self._load(tenant_id, project_id, job_id)
            if job.cancel_requested:
                self._cancel_leased(job, now)
                raise SchedulingJobCancelled("SCHEDULING_JOB_CANCELLED")
            self._require_lease(job, token, now)
            if (
                result.engine_version != job.engine_version
                or result.calculation_identity != job.calculation_identity
            ):
                raise SchedulingJobIdentityMismatch("SCHEDULING_JOB_ENGINE_IDENTITY_MISMATCH")
            self._repository.put_result(
                replace(result, persisted_at=now)
            )
            succeeded = replace(
                job,
                state=SchedulingJobState.SUCCEEDED,
                lease_owner=None,
                lease_token=None,
                lease_expires_at=None,
                updated_at=now,
                revision=job.revision + 1,
            )
            if self._repository.compare_and_set(succeeded, job.revision):
                return succeeded
            # The result row is immutable; a lost CAS means another writer
            # changed the job, so stop instead of retrying on a stale lease.
            raise SchedulingJobError("SCHEDULING_JOB_LEASE_CONTENTION")
        raise SchedulingJobError("SCHEDULING_JOB_LEASE_CONTENTION")

    def fail(
        self,
        *,
        tenant_id: str,
        project_id: str,
        job_id: str,
        token: str,
        error: str,
        retryable: bool,
    ) -> SchedulingJob:
        _require_text("error", error)
        for _ in range(self._CAS_RETRIES):
            now = self._clock()
            job = self._load(tenant_id, project_id, job_id)
            if job.cancel_requested:
                self._cancel_leased(job, now)
                raise SchedulingJobCancelled("SCHEDULING_JOB_CANCELLED")
            self._require_lease(job, token, now)
            if retryable and job.attempts < job.max_attempts:
                requeued = replace(
                    job,
                    state=SchedulingJobState.QUEUED,
                    lease_owner=None,
                    lease_token=None,
                    lease_expires_at=None,
                    last_error=error,
                    updated_at=now,
                    revision=job.revision + 1,
                )
                if self._repository.compare_and_set(requeued, job.revision):
                    return requeued
                continue
            failed = self._failed_job(job, now, error)
            if self._repository.compare_and_set(failed, job.revision):
                return failed
        raise SchedulingJobError("SCHEDULING_JOB_LEASE_CONTENTION")

    # -- cancellation -----------------------------------------------------

    def cancel(
        self, *, tenant_id: str, project_id: str, job_id: str, user_id: str
    ) -> SchedulingJob:
        for _ in range(self._CAS_RETRIES):
            now = self._clock()
            job = self._load(tenant_id, project_id, job_id)
            if not self._authorization.can_view(
                tenant_id=tenant_id,
                project_id=project_id,
                user_id=user_id,
                job=job,
            ):
                raise SchedulingJobNotFound("SCHEDULING_JOB_NOT_FOUND")
            if job.is_terminal:
                return job
            if job.state is SchedulingJobState.QUEUED:
                cancelled = replace(
                    job,
                    state=SchedulingJobState.CANCELLED,
                    cancel_requested=True,
                    cancel_requested_by=user_id,
                    updated_at=now,
                    revision=job.revision + 1,
                )
            else:
                # A lease holder may be mid-calculation. Record the request; the
                # next checkpoint, renewal, completion or lease expiry observes
                # it and terminates the job without publishing a result.
                if job.cancel_requested:
                    return job
                cancelled = replace(
                    job,
                    cancel_requested=True,
                    cancel_requested_by=user_id,
                    updated_at=now,
                    revision=job.revision + 1,
                )
            if self._repository.compare_and_set(cancelled, job.revision):
                return cancelled
        raise SchedulingJobError("SCHEDULING_JOB_CANCEL_CONTENTION")

    # -- recovery ---------------------------------------------------------

    def recover_expired(self, *, limit: int = 100) -> tuple[SchedulingJob, ...]:
        """Terminate or requeue leases whose holder disappeared."""
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise SchedulingJobError("INVALID_RECOVERY_LIMIT")
        recovered: list[SchedulingJob] = []
        for _ in range(limit):
            now = self._clock()
            expired = self._repository.find_expired_leases(now, limit=1)
            if not expired:
                break
            job = expired[0]
            if job.cancel_requested:
                updated = replace(
                    job,
                    state=SchedulingJobState.CANCELLED,
                    lease_owner=None,
                    lease_token=None,
                    lease_expires_at=None,
                    updated_at=now,
                    revision=job.revision + 1,
                )
            elif job.attempts >= job.max_attempts:
                updated = self._failed_job(job, now, "LEASE_EXPIRED")
            else:
                updated = replace(
                    job,
                    state=SchedulingJobState.QUEUED,
                    lease_owner=None,
                    lease_token=None,
                    lease_expires_at=None,
                    last_error="LEASE_EXPIRED",
                    updated_at=now,
                    revision=job.revision + 1,
                )
            if self._repository.compare_and_set(updated, job.revision):
                recovered.append(updated)
        return tuple(recovered)

    # -- internals --------------------------------------------------------

    def _load(self, tenant_id: str, project_id: str, job_id: str) -> SchedulingJob:
        job = self._repository.get(tenant_id, project_id, job_id)
        if job is None:
            raise SchedulingJobNotFound("SCHEDULING_JOB_NOT_FOUND")
        return job

    def _require_lease(self, job: SchedulingJob, token: str, now: datetime) -> None:
        if (
            job.state is not SchedulingJobState.LEASED
            or job.lease_token != token
            or job.lease_expires_at is None
            or job.lease_expires_at <= now
        ):
            raise SchedulingJobLeaseError("SCHEDULING_JOB_LEASE_NOT_HELD")

    def _failed_job(self, job: SchedulingJob, now: datetime, error: str) -> SchedulingJob:
        return replace(
            job,
            state=SchedulingJobState.FAILED,
            lease_owner=None,
            lease_token=None,
            lease_expires_at=None,
            last_error=error,
            updated_at=now,
            revision=job.revision + 1,
        )

    def _fail_leased(
        self, job: SchedulingJob, now: datetime, error: str
    ) -> SchedulingJob:
        failed = self._failed_job(job, now, error)
        if not self._repository.compare_and_set(failed, job.revision):
            raise SchedulingJobError("SCHEDULING_JOB_LEASE_CONTENTION")
        return failed

    def _cancel_leased(self, job: SchedulingJob, now: datetime) -> SchedulingJob:
        if job.state is SchedulingJobState.QUEUED:
            cancelled = replace(
                job,
                state=SchedulingJobState.CANCELLED,
                updated_at=now,
                revision=job.revision + 1,
            )
        else:
            cancelled = replace(
                job,
                state=SchedulingJobState.CANCELLED,
                lease_owner=None,
                lease_token=None,
                lease_expires_at=None,
                updated_at=now,
                revision=job.revision + 1,
            )
        if not self._repository.compare_and_set(cancelled, job.revision):
            raise SchedulingJobError("SCHEDULING_JOB_LEASE_CONTENTION")
        return cancelled
