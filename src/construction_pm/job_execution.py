from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import Callable, Protocol, Sequence


class JobState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRYABLE = "RETRYABLE"
    ROLLED_BACK = "ROLLED_BACK"
    REPLAYED = "REPLAYED"
    CONFLICT = "CONFLICT"


class JobExecutionError(ValueError):
    pass


class JobOptimisticLockConflict(JobExecutionError):
    pass


class JobIdempotencyConflict(JobExecutionError):
    pass


class JobStepFailure(RuntimeError):
    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class JobExecution:
    tenant_id: str
    project_id: str
    job_id: str
    revision: int
    state: JobState
    idempotency_key: str
    fingerprint: str
    error: str | None = None

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("job_id", self.job_id),
            ("idempotency_key", self.idempotency_key),
            ("fingerprint", self.fingerprint),
        ):
            if not isinstance(value, str) or not value.strip():
                raise JobExecutionError(f"INVALID_JOB_{name.upper()}")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 0:
            raise JobExecutionError("INVALID_JOB_REVISION")
        if not isinstance(self.state, JobState):
            raise JobExecutionError("INVALID_JOB_STATE")


@dataclass(frozen=True)
class JobExecutionOutcome:
    job_id: str
    state: JobState
    revision: int
    error: str | None = None


class JobExecutionRepository(Protocol):
    def lock_idempotency(self, tenant_id: str, project_id: str, key: str) -> None: ...
    def get_by_idempotency(self, tenant_id: str, project_id: str, key: str) -> JobExecution | None: ...
    def get_current(self, tenant_id: str, project_id: str, job_id: str) -> JobExecution | None: ...
    def put(self, execution: JobExecution) -> None: ...


class TransactionManager(Protocol):
    def transaction(self): ...


class InMemoryJobExecutionRepository:
    """Reference persistence boundary; calculations and step business logic stay outside."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str], JobExecution] = {}
        self._idempotency: dict[tuple[str, str, str], JobExecution] = {}
        self._lock = RLock()

    def lock_idempotency(self, tenant_id: str, project_id: str, key: str) -> None:
        self._lock.acquire()

    def unlock_idempotency(self) -> None:
        self._lock.release()

    def get_by_idempotency(self, tenant_id: str, project_id: str, key: str) -> JobExecution | None:
        return self._idempotency.get((tenant_id, project_id, key))

    def get_current(self, tenant_id: str, project_id: str, job_id: str) -> JobExecution | None:
        return self._records.get((tenant_id, project_id, job_id))

    def put(self, execution: JobExecution) -> None:
        execution.validate()
        job_key = (execution.tenant_id, execution.project_id, execution.job_id)
        self._records[job_key] = execution
        self._idempotency[
            (execution.tenant_id, execution.project_id, execution.idempotency_key)
        ] = execution


class _Transaction:
    def __init__(self, repository: InMemoryJobExecutionRepository) -> None:
        self.repository = repository
        self.snapshot_records = dict(repository._records)
        self.snapshot_idempotency = dict(repository._idempotency)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            self.repository._records = self.snapshot_records
            self.repository._idempotency = self.snapshot_idempotency
        self.repository.unlock_idempotency()
        return False


class InMemoryJobTransactionManager:
    def __init__(self, repository: InMemoryJobExecutionRepository) -> None:
        self.repository = repository

    def transaction(self):
        return _Transaction(self.repository)


class JobStepTransactionExecutor:
    """Application boundary for atomic ordered job steps and idempotent replay."""

    def __init__(self, repository: JobExecutionRepository, transaction_manager: TransactionManager) -> None:
        self.repository = repository
        self.transaction_manager = transaction_manager

    def execute(
        self,
        *,
        tenant_id: str,
        project_id: str,
        job_id: str,
        expected_revision: int,
        idempotency_key: str,
        steps: Sequence[Callable[[], None]],
    ) -> JobExecutionOutcome:
        fingerprint = _fingerprint(job_id, expected_revision, len(steps))
        try:
            with self.transaction_manager.transaction():
                self.repository.lock_idempotency(tenant_id, project_id, idempotency_key)
                existing = self.repository.get_by_idempotency(
                    tenant_id, project_id, idempotency_key
                )
                if existing is not None:
                    if existing.fingerprint != fingerprint:
                        raise JobIdempotencyConflict("JOB_IDEMPOTENCY_KEY_REUSE")
                    return JobExecutionOutcome(
                        existing.job_id, JobState.REPLAYED, existing.revision, existing.error
                    )

                current = self.repository.get_current(tenant_id, project_id, job_id)
                actual_revision = 0 if current is None else current.revision
                if actual_revision != expected_revision:
                    raise JobOptimisticLockConflict("JOB_REVISION_CONFLICT")

                self.repository.put(
                    JobExecution(
                        tenant_id, project_id, job_id, actual_revision,
                        JobState.RUNNING, idempotency_key, fingerprint,
                    )
                )

                for step in steps:
                    step()

                next_revision = actual_revision + 1
                self.repository.put(
                    JobExecution(
                        tenant_id, project_id, job_id, next_revision,
                        JobState.SUCCEEDED, idempotency_key, fingerprint,
                    )
                )
                return JobExecutionOutcome(job_id, JobState.SUCCEEDED, next_revision)
        except JobOptimisticLockConflict as exc:
            current = self.repository.get_current(tenant_id, project_id, job_id)
            revision = 0 if current is None else current.revision
            return JobExecutionOutcome(job_id, JobState.CONFLICT, revision, str(exc))
        except JobStepFailure as exc:
            state = JobState.RETRYABLE if exc.retryable else JobState.FAILED
            with self.transaction_manager.transaction():
                self.repository.lock_idempotency(tenant_id, project_id, idempotency_key)
                current = self.repository.get_current(tenant_id, project_id, job_id)
                revision = 0 if current is None else current.revision
                self.repository.put(
                    JobExecution(
                        tenant_id, project_id, job_id, revision,
                        JobState.ROLLED_BACK, idempotency_key, fingerprint, str(exc),
                    )
                )
            return JobExecutionOutcome(job_id, state, revision, str(exc))


def _fingerprint(job_id: str, expected_revision: int, step_count: int) -> str:
    payload = json.dumps(
        {"job_id": job_id, "expected_revision": expected_revision, "step_count": step_count},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
