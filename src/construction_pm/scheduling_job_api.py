"""Application API for durable, asynchronous authoritative scheduling runs.

The synchronous ``POST /api/v1/schedule/query`` route stays exactly as it is.
This module adds the durable path a deployment needs when a run is too large to
hold an HTTP request open: submit once, let a worker calculate on the P0-N
engine, then read status and result by job id.

Ownership boundaries
--------------------
* Identity and authorization come from the caller (the HTTP layer opens the
  project and passes the authenticated user and roles). The API never trusts a
  body-supplied tenant, project, revision or user.
* The job stores the immutable run parameters it will need after a worker
  restart (snapshot id, project revision, submitter roles). A job without them
  fails closed instead of guessing an input.
* Failures are typed and mapped to one stable error code per condition.
"""

from __future__ import annotations

import hmac
import json
from dataclasses import dataclass

from .backend_p0.models import BackendScope
from .schedule_input_snapshot_repository import ScheduleInputSnapshotRepository
from .scheduling_job_lifecycle import (
    SchedulingJob,
    SchedulingJobError,
    SchedulingJobIdentityMismatch,
    SchedulingJobNotFound,
    SchedulingJobRequest,
    SchedulingJobResult,
    SchedulingJobResultError,
    SchedulingJobService,
    SchedulingJobStateError,
)
from .scheduling_job_runner import (
    SchedulingEngineJobRunner,
    request_fingerprint,
)


SCHEDULING_JOB_CONTRACT = "scheduling-job.v1"
DEFAULT_ENGINE_VERSION = "cubi-26.0.0"


def canonical_roles(roles: frozenset[str]) -> str:
    """Roles travel with the job so a restarted worker keeps the same scope."""
    return json.dumps(sorted(roles), separators=(",", ":"))



class SchedulingJobAPIError(ValueError):
    """A request the API refuses, with one stable machine code."""

    def __init__(self, code: str, *, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class SchedulingJobScope:
    """The authenticated project scope the caller already opened."""

    tenant_id: str
    project_id: str
    project_revision: int
    user_id: str
    roles: frozenset[str]


@dataclass(frozen=True)
class SchedulingJobView:
    job: SchedulingJob
    deduplicated: bool = False

    def as_dict(self, *, result: SchedulingJobResult | None = None) -> dict[str, object]:
        job = self.job
        payload: dict[str, object] = {
            "contract_version": SCHEDULING_JOB_CONTRACT,
            "job_id": job.job_id,
            "tenant_id": job.tenant_id,
            "project_id": job.project_id,
            "state": job.state.value,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
            "engine_version": job.engine_version,
            "calculation_identity": job.calculation_identity,
            "request_fingerprint": job.request_fingerprint,
            "submitted_by": job.submitted_by,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "cancel_requested": job.cancel_requested,
            "last_error": job.last_error,
            "revision": job.revision,
            "deduplicated": self.deduplicated,
        }
        if result is not None:
            payload["result"] = {
                "output_hash": result.output_hash,
                "payload": dict(result.payload),
                "persisted_at": result.persisted_at.isoformat(),
            }
        return payload


class SchedulingJobAPI:
    """Transport-neutral submission, status, result, cancel and worker tick."""

    def __init__(
        self,
        service: SchedulingJobService,
        *,
        runner: SchedulingEngineJobRunner | None = None,
        worker_token: str | None = None,
        snapshot_repository: ScheduleInputSnapshotRepository | None = None,
    ) -> None:
        self._service = service
        self._runner = runner
        self._worker_token = worker_token
        self._snapshot_repository = snapshot_repository

    # -- submission -------------------------------------------------------

    def submit(
        self,
        scope: SchedulingJobScope,
        *,
        snapshot_id: object,
        engine_version: object = DEFAULT_ENGINE_VERSION,
        calculation_identity: object | None = None,
        activity_count: object | None = None,
        relationship_count: object | None = None,
    ) -> SchedulingJobView:
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            raise SchedulingJobAPIError("SCHEDULING_JOB_SNAPSHOT_REQUIRED")
        if not isinstance(engine_version, str) or not engine_version.strip():
            raise SchedulingJobAPIError("SCHEDULING_JOB_ENGINE_VERSION_REQUIRED")
        identity = calculation_identity
        if self._snapshot_repository is not None:
            snapshot_identity, snapshot_activity_count, snapshot_relationship_count = (
                self._resolve_snapshot(
                    scope,
                    snapshot_id=snapshot_id,
                    activity_count=activity_count,
                    relationship_count=relationship_count,
                )
            )
            if identity is None:
                identity = snapshot_identity
            elif identity != snapshot_identity:
                raise SchedulingJobAPIError(
                    "SCHEDULING_JOB_CALCULATION_IDENTITY_MISMATCH", status=409
                )
            activity_count = snapshot_activity_count
            relationship_count = snapshot_relationship_count
        if identity is None:
            identity = snapshot_id
        if not isinstance(identity, str) or not identity.strip():
            raise SchedulingJobAPIError("SCHEDULING_JOB_CALCULATION_IDENTITY_REQUIRED")
        parameters = self._run_parameters(
            scope,
            snapshot_id=snapshot_id,
            activity_count=activity_count,
            relationship_count=relationship_count,
        )
        fingerprint = request_fingerprint(
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
            project_revision=scope.project_revision,
            snapshot_id=snapshot_id,
            engine_version=engine_version,
            calculation_identity=identity,
        )
        request = SchedulingJobRequest(
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
            submitted_by=scope.user_id,
            request_fingerprint=fingerprint,
            engine_version=engine_version,
            calculation_identity=identity,
        )
        try:
            submission = self._service.submit(request, run_parameters=parameters)
        except SchedulingJobError as error:
            raise self._map_error(error) from error
        return SchedulingJobView(submission.job, submission.deduplicated)

    def _run_parameters(
        self,
        scope: SchedulingJobScope,
        *,
        snapshot_id: str,
        activity_count: object | None,
        relationship_count: object | None,
    ) -> tuple[tuple[str, str], ...]:
        if activity_count is not None and (
            isinstance(activity_count, bool) or not isinstance(activity_count, int)
            or activity_count < 0
        ):
            raise SchedulingJobAPIError("SCHEDULING_JOB_ACTIVITY_COUNT_INVALID")
        if relationship_count is not None and (
            isinstance(relationship_count, bool) or not isinstance(relationship_count, int)
            or relationship_count < 0
        ):
            raise SchedulingJobAPIError("SCHEDULING_JOB_RELATIONSHIP_COUNT_INVALID")
        parameters = {
            "snapshot_id": snapshot_id,
            "project_revision": str(scope.project_revision),
            "roles": canonical_roles(scope.roles),
        }
        if activity_count is not None:
            parameters["activity_count"] = str(activity_count)
        if relationship_count is not None:
            parameters["relationship_count"] = str(relationship_count)
        return tuple(sorted(parameters.items()))

    def _resolve_snapshot(
        self,
        scope: SchedulingJobScope,
        *,
        snapshot_id: str,
        activity_count: object | None,
        relationship_count: object | None,
    ) -> tuple[str, int, int]:
        """Bind the job to an immutable snapshot the caller is allowed to read.

        The calculation identity is the snapshot's own identity, never a
        caller-supplied string, so a job can only publish a result that agrees
        with the input it was submitted for.
        """
        snapshot = self._snapshot_repository.get(
            BackendScope(scope.tenant_id, scope.project_id, scope.project_revision),
            snapshot_id,
        )  # type: ignore[union-attr]
        if snapshot is None:
            raise SchedulingJobAPIError("SCHEDULING_JOB_SNAPSHOT_NOT_FOUND", status=404)
        payload = json.loads(snapshot.canonical_payload)
        activities = payload.get("activities") or []
        relationships = payload.get("relationships") or []
        expected_activity_count = len(activities) if isinstance(activities, list) else 0
        expected_relationship_count = (
            len(relationships) if isinstance(relationships, list) else 0
        )
        if (
            activity_count is not None
            and activity_count != expected_activity_count
        ) or (
            relationship_count is not None
            and relationship_count != expected_relationship_count
        ):
            raise SchedulingJobAPIError("SCHEDULING_JOB_WORKLOAD_MISMATCH", status=409)
        return (
            snapshot.calculation_identity,
            expected_activity_count,
            expected_relationship_count,
        )

    # -- reads ------------------------------------------------------------

    def status(self, scope: SchedulingJobScope, job_id: str) -> SchedulingJobView:
        job = self._load(scope, job_id)
        return SchedulingJobView(job)

    def result_payload(
        self, scope: SchedulingJobScope, job_id: str
    ) -> dict[str, object]:
        job = self._load(scope, job_id)
        try:
            stored = self._service.get_result(
                tenant_id=job.tenant_id,
                project_id=job.project_id,
                job_id=job.job_id,
                user_id=scope.user_id,
            )
        except (SchedulingJobResultError, SchedulingJobNotFound, SchedulingJobIdentityMismatch) as error:
            raise self._map_error(error) from error
        return SchedulingJobView(job).as_dict(result=stored)

    def cancel(self, scope: SchedulingJobScope, job_id: str) -> SchedulingJobView:
        try:
            job = self._service.cancel(
                tenant_id=scope.tenant_id,
                project_id=scope.project_id,
                job_id=job_id,
                user_id=scope.user_id,
            )
        except SchedulingJobError as error:
            raise self._map_error(error) from error
        return SchedulingJobView(job)

    # -- worker control ---------------------------------------------------

    def worker_status(
        self, *, token: str | None = None, require_token: bool = True
    ) -> dict[str, object]:
        if require_token:
            self._require_worker_token(token)
        if self._runner is None:
            raise SchedulingJobAPIError("SCHEDULING_WORKER_NOT_CONFIGURED", status=503)
        return {
            "contract_version": SCHEDULING_JOB_CONTRACT,
            "worker": self._runner.snapshot(),
        }

    def tick(
        self,
        *,
        token: str | None,
        timeout: float | None = None,
        require_token: bool = True,
    ) -> dict[str, object]:
        if require_token:
            self._require_worker_token(token)
        if self._runner is None:
            raise SchedulingJobAPIError("SCHEDULING_WORKER_NOT_CONFIGURED", status=503)
        if timeout is not None and (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or timeout <= 0
            or timeout > 300
        ):
            raise SchedulingJobAPIError("SCHEDULING_WORKER_TIMEOUT_INVALID")
        outcome, idle = self._runner.drain(timeout=timeout)
        return {
            "contract_version": SCHEDULING_JOB_CONTRACT,
            "outcome": outcome.as_dict(),
            "idle": idle,
            "worker": self._runner.snapshot(),
        }

    def _require_worker_token(self, token: str | None) -> None:
        expected = self._worker_token
        if not expected:
            # No token configured means no worker endpoint at all: a
            # misconfigured deployment must not expose anonymous execution.
            raise SchedulingJobAPIError("SCHEDULING_WORKER_DISABLED", status=404)
        if not isinstance(token, str) or not hmac.compare_digest(token, expected):
            raise SchedulingJobAPIError("SCHEDULING_WORKER_UNAUTHORIZED", status=403)

    # -- internals --------------------------------------------------------

    def _load(self, scope: SchedulingJobScope, job_id: str) -> SchedulingJob:
        if not isinstance(job_id, str) or not job_id.strip():
            raise SchedulingJobAPIError("SCHEDULING_JOB_ID_REQUIRED")
        try:
            return self._service.get(
                tenant_id=scope.tenant_id,
                project_id=scope.project_id,
                job_id=job_id,
                user_id=scope.user_id,
            )
        except SchedulingJobNotFound as error:
            raise SchedulingJobAPIError("SCHEDULING_JOB_NOT_FOUND", status=404) from error

    @staticmethod
    def _map_error(error: Exception) -> SchedulingJobAPIError:
        code = str(error) or type(error).__name__
        if isinstance(error, SchedulingJobNotFound):
            return SchedulingJobAPIError("SCHEDULING_JOB_NOT_FOUND", status=404)
        if isinstance(error, SchedulingJobStateError):
            return SchedulingJobAPIError(code, status=409)
        if isinstance(error, SchedulingJobResultError):
            return SchedulingJobAPIError(code, status=409)
        if isinstance(error, SchedulingJobIdentityMismatch):
            return SchedulingJobAPIError(code, status=409)
        if isinstance(error, SchedulingJobError):
            return SchedulingJobAPIError(code, status=400)
        return SchedulingJobAPIError(code, status=500)
