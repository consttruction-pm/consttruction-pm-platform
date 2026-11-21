"""P0-N production bridge: run durable scheduling jobs on the optimized engine.

A scheduled run is submitted through the HTTP API, stored by the durable job
lifecycle, and executed by a worker that this module owns. The worker is one
``SchedulingJobExecutor`` over the process-wide ``GlobalExecutionBudget``:
placement (one project per process), slot allocation and the result cache are
the P0-N components, so the API path and the benchmark path measure the same
engine instead of two divergent ones.

Safety rules kept explicit here
-------------------------------
* ``thread`` is the default. ``process`` requires either a provider factory or a
  ``child_database_url`` so the forked child builds its own repositories; a child
  must never reuse a parent database connection.
* A job without stored run parameters fails closed; it is never guessed from
  the latest snapshot.
* The worker never widens the job's authorization scope: the calculation runs
  with the submitted user's roles and the job's own tenant/project.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from functools import partial
from typing import Callable, Mapping

from .application.authorization import AuthorizationContext
from .backend_p0.authoritative_schedule_query import AuthoritativeScheduleQueryProvider
from .backend_p0.errors import BackendApplicationError
from .control_intelligence.contracts import ControlScope
from .control_intelligence.query import ScheduleQueryKind, ScheduleQueryRequest
from .scheduling.time_schedule import FloatExecutionPolicy
from .scheduling_execution_budget import GlobalExecutionBudget, global_execution_budget
from .scheduling_job_executor import (
    SchedulingExecutionError,
    SchedulingExecutionSummary,
    SchedulingJobExecutor,
)
from .scheduling_job_lifecycle import (
    SchedulingJob,
    SchedulingJobResult,
    SchedulingJobService,
)
from .scheduling_result_cache import ScheduleResultCache
from .scheduling_worker_scheduler import (
    ProjectWorkload,
    SlotAllocationPolicy,
    make_slot_admission,
)


class SchedulingJobRunnerError(ValueError):
    """The worker cannot run this job as configured."""


_PARAMETER_SNAPSHOT = "snapshot_id"
_PARAMETER_REVISION = "project_revision"
_PARAMETER_ROLES = "roles"


def job_authorization_context(job: SchedulingJob) -> AuthorizationContext:
    """Rebuild the submitter's scope from the immutable job parameters."""
    parameters = job.run_parameter_map()
    try:
        roles = json.loads(parameters.get(_PARAMETER_ROLES, "[]"))
    except ValueError as error:
        raise SchedulingJobRunnerError("SCHEDULING_JOB_PARAMETERS_INVALID") from error
    if not isinstance(roles, list) or any(not isinstance(role, str) for role in roles):
        raise SchedulingJobRunnerError("SCHEDULING_JOB_PARAMETERS_INVALID")
    return AuthorizationContext(
        tenant_id=job.tenant_id,
        project_id=job.project_id,
        user_id=job.submitted_by,
        roles=frozenset(roles),
    )


def job_snapshot_id(job: SchedulingJob) -> str:
    snapshot_id = job.run_parameter_map().get(_PARAMETER_SNAPSHOT)
    if not snapshot_id:
        # Fail closed: an old or hand-written job has no immutable input.
        raise SchedulingJobRunnerError("SCHEDULING_JOB_SNAPSHOT_MISSING")
    return snapshot_id


def _job_query(job: SchedulingJob) -> ScheduleQueryRequest:
    parameters = job.run_parameter_map()
    raw_revision = parameters.get(_PARAMETER_REVISION)
    try:
        revision = int(raw_revision) if raw_revision is not None else None
    except ValueError as error:
        raise SchedulingJobRunnerError("SCHEDULING_JOB_PARAMETERS_INVALID") from error
    if revision is None:
        raise SchedulingJobRunnerError("SCHEDULING_JOB_PARAMETERS_INVALID")
    return ScheduleQueryRequest(
        query_id=job.job_id,
        scope=ControlScope(job.tenant_id, job.project_id, revision),
        requested_by=job.submitted_by,
        query_text="authoritative schedule run",
        kind=ScheduleQueryKind.FACT,
        language="en",
        constraints={"snapshot_id": job_snapshot_id(job)},
    )


@dataclass(frozen=True)
class SchedulingJobRunOutcome:
    claimed: int
    succeeded: int
    failed: int
    cancelled: int
    retried: int
    lease_lost: int
    process_starts: int
    inline_fallbacks: int
    cache_hits: int
    cache_misses: int
    peak_slots: int
    stopped: bool

    def as_dict(self) -> dict[str, int | bool]:
        return {
            "claimed": self.claimed,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "cancelled": self.cancelled,
            "retried": self.retried,
            "lease_lost": self.lease_lost,
            "process_starts": self.process_starts,
            "inline_fallbacks": self.inline_fallbacks,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "peak_slots": self.peak_slots,
            "stopped": self.stopped,
        }


class SchedulingEngineJobRunner:
    """One worker: durable queue, global budget, P0-N placement and cache."""

    def __init__(
        self,
        service: SchedulingJobService,
        *,
        provider: AuthoritativeScheduleQueryProvider | None,
        provider_factory: Callable[[], AuthoritativeScheduleQueryProvider] | None = None,
        child_database_url: str | None = None,
        execution_mode: str = "thread",
        owner: str = "scheduling-worker",
        budget: GlobalExecutionBudget | None = None,
        slot_policy: SlotAllocationPolicy | None = None,
        result_cache: ScheduleResultCache | None = None,
        job_timeout: float | None = None,
        start_method: str | None = None,
        poll_interval: float = 0.05,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if execution_mode not in ("thread", "process"):
            raise SchedulingJobRunnerError("INVALID_EXECUTION_MODE")
        if execution_mode == "process" and child_database_url is None and provider_factory is None:
            # A forked child cannot safely reuse the parent's database
            # connection; without a way to build its own it would corrupt state.
            raise SchedulingJobRunnerError("PROCESS_MODE_REQUIRES_PROVIDER_FACTORY")
        if execution_mode == "process" and child_database_url is not None and provider_factory is not None:
            raise SchedulingJobRunnerError("PROCESS_MODE_FACTORY_CONFLICT")
        if execution_mode == "thread" and provider is None:
            raise SchedulingJobRunnerError("THREAD_MODE_REQUIRES_PROVIDER")
        if job_timeout is not None and job_timeout <= 0:
            raise SchedulingJobRunnerError("INVALID_JOB_TIMEOUT")
        self._service = service
        self._provider = provider
        self._provider_factory = provider_factory
        self._child_database_url = child_database_url
        self._execution_mode = execution_mode
        self._owner = owner
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._slot_policy = slot_policy or SlotAllocationPolicy()
        self._result_cache = result_cache
        self._budget = budget or global_execution_budget()

        executor_kwargs: dict[str, object] = {
            "owner": owner,
            "budget": self._budget,
            "poll_interval": poll_interval,
            "clock": self._clock,
            "execution_mode": execution_mode,
        }
        if execution_mode == "process":
            if child_database_url is not None:
                # The pickled callables must be self-contained: the child opens
                # its own database connection and rebuilds the provider. Only a
                # DSN string crosses the process boundary.
                calculate_with_slots = partial(
                    run_scheduled_job_in_child, child_database_url
                )
            else:
                calculate = self._calculate
                calculate_with_slots = self._calculate_with_slots
            executor_kwargs.update(
                slot_policy=self._slot_policy,
                workload_estimator=self._estimate_workload,
                result_cache=self._result_cache,
                calculate_with_slots=calculate_with_slots,
                job_timeout=job_timeout,
            )
            if start_method is not None:
                executor_kwargs["start_method"] = start_method
        self._executor = SchedulingJobExecutor(
            service,
            calculate=self._calculate if child_database_url is None else partial(
                run_scheduled_job_in_child, child_database_url
            ),
            **executor_kwargs,  # type: ignore[arg-type]
        )

    # -- properties -------------------------------------------------------

    @property
    def execution_mode(self) -> str:
        return self._execution_mode

    @property
    def executor(self) -> SchedulingJobExecutor:
        return self._executor

    @property
    def service(self) -> SchedulingJobService:
        """The lifecycle this worker claims from (also used by composition)."""
        return self._service

    @property
    def budget(self) -> GlobalExecutionBudget:
        return self._budget

    # -- calculation ------------------------------------------------------

    def _provider_for(self, slots: int) -> AuthoritativeScheduleQueryProvider:
        if self._provider_factory is not None:
            provider = self._provider_factory()
        elif self._provider is not None:
            provider = self._provider
        else:  # pragma: no cover - constructor rejects this state
            raise SchedulingJobRunnerError("PROVIDER_UNAVAILABLE")
        if slots <= 1:
            return provider
        workers = max(1, slots - 1)
        return replace(
            provider,
            float_execution=FloatExecutionPolicy(
                workers=workers,
                admission=make_slot_admission(slots),
                allow_nested_fork=workers > 1,
            ),
        )

    def _result_for(
        self, job: SchedulingJob, slots: int
    ) -> SchedulingJobResult:
        provider = self._provider_for(slots)
        return execute_job_with_provider(provider, job, self._clock())

    def _calculate(self, job: SchedulingJob) -> SchedulingJobResult:
        return self._result_for(job, 1)

    def _calculate_with_slots(
        self, job: SchedulingJob, slots: int
    ) -> SchedulingJobResult:
        return self._result_for(job, slots)

    # -- queue hints ------------------------------------------------------

    def _estimate_workload(self, job: SchedulingJob) -> ProjectWorkload | None:
        parameters = job.run_parameter_map()
        try:
            activity_count = int(parameters["activity_count"])
            relationship_count = int(parameters["relationship_count"])
        except (KeyError, ValueError):
            return None
        return ProjectWorkload(activity_count, relationship_count)

    # -- worker entry points ----------------------------------------------

    def run_once(self) -> tuple[SchedulingJobRunOutcome, bool]:
        before = self._executor.summary()
        ran = self._executor.run_once()
        return self._delta(before, self._executor.summary()), ran

    def drain(
        self, *, timeout: float | None = None
    ) -> tuple[SchedulingJobRunOutcome, bool]:
        before = self._executor.summary()
        # A tick must also recover leases left by a stopped worker; the idle
        # loop alone only looks at pending work, so a crashed claim would
        # otherwise never be requeued.
        self._service.recover_expired(limit=100)
        self._executor.run_until_idle(timeout=timeout)
        after = self._executor.summary()
        return self._delta(before, after), self._executor.in_flight() == 0

    @staticmethod
    def _delta(
        before: SchedulingExecutionSummary, after: SchedulingExecutionSummary
    ) -> SchedulingJobRunOutcome:
        return SchedulingJobRunOutcome(
            claimed=after.claimed - before.claimed,
            succeeded=after.succeeded - before.succeeded,
            failed=after.failed - before.failed,
            cancelled=after.cancelled - before.cancelled,
            retried=after.retried - before.retried,
            lease_lost=after.lease_lost - before.lease_lost,
            process_starts=after.process_starts - before.process_starts,
            inline_fallbacks=after.inline_fallbacks - before.inline_fallbacks,
            cache_hits=after.cache_hits - before.cache_hits,
            cache_misses=after.cache_misses - before.cache_misses,
            peak_slots=after.peak_slots,
            stopped=after.stopped,
        )

    def request_stop(self) -> None:
        self._executor.request_stop()

    def snapshot(self) -> dict[str, object]:
        """Worker health/telemetry for the operations endpoint."""
        return {
            "execution_mode": self._execution_mode,
            "owner": self._owner,
            "budget_slots": self._budget.workers,
            "budget_active": self._budget.active,
            "budget_peak": self._budget.peak,
            "in_flight": self._executor.in_flight(),
            "cache": None if self._result_cache is None else self._result_cache.stats(),
        }


def execute_job_with_provider(
    provider: AuthoritativeScheduleQueryProvider,
    job: SchedulingJob,
    persisted_at: datetime,
) -> SchedulingJobResult:
    """Run one immutable job and keep the stable rejection code on failure.

    The provider translates core/validation failures into
    ``BackendApplicationError``; its ``__str__`` is a generic user message, so
    a durable job's error must carry the stable code instead. That is what
    makes a failed run diagnosable (for example a calendar that is not
    registered for the snapshot's scope).
    """
    try:
        answer = provider.execute(
            _job_query(job),
            auth_context=job_authorization_context(job),
        )
    except BackendApplicationError as error:
        raise SchedulingExecutionError(
            f"{error.category.value}:{error.code}", retryable=error.retryable
        ) from error
    return answer_to_job_result(job, answer, persisted_at)


def answer_to_job_result(
    job: SchedulingJob,
    answer: object,
    persisted_at: datetime,
) -> SchedulingJobResult:
    """Project one authoritative query answer onto the durable result row."""
    source_refs = tuple(getattr(answer, "source_refs", ()) or ())
    if not source_refs:
        raise SchedulingJobRunnerError("SCHEDULING_JOB_RESULT_WITHOUT_SOURCE")
    data = getattr(answer, "data", None)
    if not isinstance(data, Mapping):
        raise SchedulingJobRunnerError("SCHEDULING_JOB_RESULT_INVALID")
    return SchedulingJobResult(
        tenant_id=job.tenant_id,
        project_id=job.project_id,
        job_id=job.job_id,
        engine_version=job.engine_version,
        calculation_identity=job.calculation_identity,
        output_hash=source_refs[0].content_hash,
        payload=dict(data),
        persisted_at=persisted_at,
    )


def run_scheduled_job_in_child(
    database_url: str,
    job: SchedulingJob,
    slots: int = 1,
) -> SchedulingJobResult:
    """Calculate one job in a child process with its own database connection.

    This function is the only thing that crosses the process boundary in
    production process mode: the DSN string and the immutable job. The child
    builds every repository itself, so no parent connection, cursor or lock is
    inherited. A dedicated process is single-threaded and non-daemonic, which
    is the condition under which the engine may fork its float workers inside
    the granted ``slots``.
    """
    import psycopg

    from .calendar_exception_repository import PostgresCalendarExceptionRepository
    from .calendar_master_repository import PostgresCalendarMasterRepository
    from .calendar_snapshot_repository import PostgresCalendarSnapshotRepository
    from .calendar_work_hours_repository import PostgresCalendarWorkHourRepository
    from .p6_versioned_resource_calendar_resolver import (
        build_calendar_registry_for_scope,
    )
    from .schedule_calculation_context_repository import (
        PostgresCalculationContextRepository,
    )
    from .schedule_input_snapshot_repository import (
        PostgresScheduleInputSnapshotRepository,
    )

    connection = psycopg.connect(
        database_url,
        autocommit=True,
        options="-c statement_timeout=600000",
    )
    try:
        master_repository = PostgresCalendarMasterRepository(connection)
        calendar_snapshot_repository = PostgresCalendarSnapshotRepository(connection)
        exception_repository = PostgresCalendarExceptionRepository(connection)
        work_hours_repository = PostgresCalendarWorkHourRepository(connection)

        def scoped_factory(scope):
            return build_calendar_registry_for_scope(
                scope=scope,
                calendar_repository=master_repository,
                snapshot_repository=calendar_snapshot_repository,
                exception_repository=exception_repository,
                work_hours_repository=work_hours_repository,
            )

        provider = AuthoritativeScheduleQueryProvider(
            snapshot_repository=PostgresScheduleInputSnapshotRepository(connection),
            scoped_calendar_registry_factory=scoped_factory,
            calculation_context_repository=PostgresCalculationContextRepository(
                connection
            ),
        )
        if slots > 1:
            provider = replace(
                provider,
                float_execution=FloatExecutionPolicy(
                    workers=max(1, slots - 1),
                    admission=make_slot_admission(slots),
                    allow_nested_fork=True,
                ),
            )
        return execute_job_with_provider(
            provider, job, datetime.now(timezone.utc)
        )
    finally:
        connection.close()


def request_fingerprint(
    *,
    tenant_id: str,
    project_id: str,
    project_revision: int,
    snapshot_id: str,
    engine_version: str,
    calculation_identity: str,
) -> str:
    """Stable identity of one immutable scheduling input.

    Two submits with the same fingerprint are the same run, so the lifecycle
    de-duplicates them instead of calculating twice.
    """
    material = json.dumps(
        {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "project_revision": project_revision,
            "snapshot_id": snapshot_id,
            "engine_version": engine_version,
            "calculation_identity": calculation_identity,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
