"""P0-N production job integration: submit, execute, read status and result.

The transport-neutral API and the engine worker are exercised here against the
real authoritative provider over a persisted snapshot. Nothing is stubbed
between ``SchedulingJobAPI.submit`` and the calculation: the job is stored by
the durable lifecycle, claimed by ``SchedulingJobExecutor`` under the global
budget, calculated by ``AuthoritativeScheduleQueryProvider`` and the published
hash is compared with a direct provider execution of the same snapshot.
"""

from __future__ import annotations

import multiprocessing
import sqlite3
import threading
import time
from datetime import date, datetime, timedelta, timezone

import pytest

from construction_pm.application.authorization import AuthorizationContext
from construction_pm.backend_p0.authoritative_schedule_query import (
    AuthoritativeScheduleQueryProvider,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.control_intelligence.contracts import ControlScope
from construction_pm.control_intelligence.query import (
    ScheduleQueryKind,
    ScheduleQueryRequest,
)
from construction_pm.schedule_calculation_context_repository import (
    SQLiteCalculationContextRepository,
    build_persisted_context,
)
from construction_pm.schedule_input_snapshot_repository import (
    SQLiteScheduleInputSnapshotRepository,
    build_snapshot,
)
from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import (
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
)
from construction_pm.scheduling_execution_budget import GlobalExecutionBudget
from construction_pm.scheduling_job_api import (
    SchedulingJobAPI,
    SchedulingJobAPIError,
    SchedulingJobScope,
)
from construction_pm.scheduling_job_lifecycle import (
    InMemorySchedulingJobRepository,
    SchedulingJobError,
    SchedulingJobRequest,
    SchedulingJobService,
    SchedulingJobState,
)
from construction_pm.scheduling_job_runner import (
    SchedulingEngineJobRunner,
    SchedulingJobRunnerError,
)
from construction_pm.scheduling_result_cache import ScheduleResultCache

TENANT = "tenant-prod"
PROJECT = "project-prod"
SNAPSHOT_ID = "S-PROD"
ENGINE = "cubi-26.0.0"
REVISION = 4
ROLES = frozenset({"project_admin"})

# Process-mode children inherit these through fork; the factory opens its own
# connection to the same file database, which is the production requirement.
_PROCESS_STATE: dict[str, object] = {}


def _fixture(database: str = ":memory:") -> tuple[
    AuthoritativeScheduleQueryProvider, str
]:
    calendar = CalendarReference("CAL-1", "1")
    source = AuthoritativeScheduleInput(
        snapshot_id=SNAPSHOT_ID,
        tenant_id=TENANT,
        project_id=PROJECT,
        project_revision=REVISION,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=calendar,
        activities=(Activity("A", 2), Activity("B", 3), Activity("C", 1)),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id=PROJECT,
        project_version=REVISION,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00",
        input_snapshot_id=SNAPSHOT_ID,
        tenant_id=TENANT,
    )
    connection = sqlite3.connect(database, check_same_thread=False)
    snapshots = SQLiteScheduleInputSnapshotRepository(connection)
    contexts = SQLiteCalculationContextRepository(connection)
    snapshots.save(
        build_snapshot(source, context, datetime(2026, 9, 30, tzinfo=timezone.utc))
    )
    contexts.save(build_persisted_context(BackendScope(TENANT, PROJECT, REVISION), context))
    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    provider = AuthoritativeScheduleQueryProvider(
        snapshots,
        lambda: registry,
        calculation_context_repository=contexts,
    )
    return provider, _direct_hash(provider)


def _direct_hash(provider: AuthoritativeScheduleQueryProvider) -> str:
    request = ScheduleQueryRequest(
        query_id="direct",
        scope=ControlScope(TENANT, PROJECT, REVISION),
        requested_by="alice",
        query_text="authoritative schedule run",
        kind=ScheduleQueryKind.FACT,
        language="en",
        constraints={"snapshot_id": SNAPSHOT_ID},
    )
    answer = provider.execute(
        request,
        auth_context=AuthorizationContext(TENANT, PROJECT, "alice", ROLES),
    )
    return answer.source_refs[0].content_hash


def _scope(
    *,
    tenant: str = TENANT,
    project: str = PROJECT,
    revision: int = REVISION,
    user: str = "alice",
) -> SchedulingJobScope:
    return SchedulingJobScope(tenant, project, revision, user, ROLES)


def _api(
    provider: AuthoritativeScheduleQueryProvider,
    *,
    repository=None,
    budget: int = 2,
    token: str | None = "worker-token",
    snapshot_repository=None,
) -> tuple[SchedulingJobAPI, SchedulingJobService, SchedulingEngineJobRunner]:
    repository = repository or InMemorySchedulingJobRepository()
    service = SchedulingJobService(repository)
    runner = SchedulingEngineJobRunner(
        service,
        provider=provider,
        budget=GlobalExecutionBudget(budget),
        poll_interval=0.002,
    )
    api = SchedulingJobAPI(
        service,
        runner=runner,
        worker_token=token,
        snapshot_repository=snapshot_repository,
    )
    return api, service, runner


def test_submit_drain_status_and_result_match_the_direct_engine_hash():
    provider, expected_hash = _fixture()
    api, _, runner = _api(provider, snapshot_repository=provider.snapshot_repository)

    submitted = api.submit(_scope(), snapshot_id=SNAPSHOT_ID)
    assert submitted.deduplicated is False
    assert submitted.job.state is SchedulingJobState.QUEUED
    assert runner.execution_mode == "thread"

    outcome = api.tick(token="worker-token")
    assert outcome["outcome"]["claimed"] == 1
    assert outcome["outcome"]["succeeded"] == 1
    assert outcome["idle"] is True

    view = api.status(_scope(), submitted.job.job_id)
    assert view.as_dict()["state"] == "SUCCEEDED"

    result = api.result_payload(_scope(), submitted.job.job_id)
    assert result["result"]["output_hash"] == expected_hash
    assert result["result"]["payload"]["activity_count"] == 3
    assert result["contract_version"] == "scheduling-job.v1"


def test_single_flight_deduplicates_a_queued_submission():
    provider, _ = _fixture()
    api, _, _ = _api(provider, snapshot_repository=provider.snapshot_repository)

    first = api.submit(_scope(), snapshot_id=SNAPSHOT_ID)
    second = api.submit(_scope(), snapshot_id=SNAPSHOT_ID)
    assert second.deduplicated is True
    assert second.job.job_id == first.job.job_id

    api.tick(token="worker-token")
    third = api.submit(_scope(), snapshot_id=SNAPSHOT_ID)
    # A terminal run is complete; a new submission is a new generation, never a
    # silently reused result.
    assert third.deduplicated is False
    assert third.job.job_id != first.job.job_id


def test_same_fingerprint_with_different_run_parameters_conflicts():
    service = SchedulingJobService(InMemorySchedulingJobRepository())
    request = SchedulingJobRequest(
        tenant_id=TENANT,
        project_id=PROJECT,
        submitted_by="alice",
        request_fingerprint="fp-shared",
        engine_version=ENGINE,
        calculation_identity="calc-shared",
    )
    service.submit(request, run_parameters=(("snapshot_id", "S1"),))
    with pytest.raises(SchedulingJobError) as error:
        service.submit(request, run_parameters=(("snapshot_id", "S2"),))
    assert str(error.value) == "SCHEDULING_JOB_PARAMETER_CONFLICT"


def test_other_tenant_and_project_cannot_read_the_job():
    provider, _ = _fixture()
    api, _, _ = _api(provider, snapshot_repository=provider.snapshot_repository)
    job = api.submit(_scope(), snapshot_id=SNAPSHOT_ID).job

    with pytest.raises(SchedulingJobAPIError) as error:
        api.status(_scope(tenant="tenant-other"), job.job_id)
    assert error.value.status == 404
    with pytest.raises(SchedulingJobAPIError):
        api.status(_scope(project="project-other"), job.job_id)
    with pytest.raises(SchedulingJobAPIError):
        api.result_payload(_scope(tenant="tenant-other"), job.job_id)


def test_cancel_before_execution_prevents_the_calculation():
    provider, _ = _fixture()
    api, _, _ = _api(provider, snapshot_repository=provider.snapshot_repository)
    job = api.submit(_scope(), snapshot_id=SNAPSHOT_ID).job

    cancelled = api.cancel(_scope(), job.job_id)
    assert cancelled.as_dict()["cancel_requested"] is True

    outcome = api.tick(token="worker-token")
    assert outcome["outcome"]["succeeded"] == 0
    assert api.status(_scope(), job.job_id).as_dict()["state"] == "CANCELLED"
    with pytest.raises(SchedulingJobAPIError) as error:
        api.result_payload(_scope(), job.job_id)
    assert error.value.status == 409
    assert error.value.code == "SCHEDULING_JOB_NOT_SUCCEEDED"


def test_snapshot_must_exist_in_scope_and_workload_hints_must_agree():
    provider, _ = _fixture()
    api, _, _ = _api(provider, snapshot_repository=provider.snapshot_repository)

    with pytest.raises(SchedulingJobAPIError) as missing:
        api.submit(_scope(), snapshot_id="S-UNKNOWN")
    assert missing.value.status == 404
    assert missing.value.code == "SCHEDULING_JOB_SNAPSHOT_NOT_FOUND"

    with pytest.raises(SchedulingJobAPIError) as workload:
        api.submit(_scope(), snapshot_id=SNAPSHOT_ID, activity_count=99)
    assert workload.value.status == 409

    with pytest.raises(SchedulingJobAPIError) as identity:
        api.submit(_scope(), snapshot_id=SNAPSHOT_ID, calculation_identity="calc-other")
    assert identity.value.status == 409
    assert identity.value.code == "SCHEDULING_JOB_CALCULATION_IDENTITY_MISMATCH"


def test_job_uses_the_snapshot_calculation_identity_not_the_caller_string():
    provider, _ = _fixture()
    api, _, _ = _api(provider, snapshot_repository=provider.snapshot_repository)
    job = api.submit(_scope(), snapshot_id=SNAPSHOT_ID).job
    snapshot = provider.snapshot_repository.get(
        BackendScope(TENANT, PROJECT, REVISION), SNAPSHOT_ID
    )
    assert job.calculation_identity == snapshot.calculation_identity


def test_worker_token_guards_tick_and_status():
    provider, _ = _fixture()
    api, _, _ = _api(provider, snapshot_repository=provider.snapshot_repository)

    with pytest.raises(SchedulingJobAPIError) as missing:
        api.tick(token=None)
    assert missing.value.status == 403
    with pytest.raises(SchedulingJobAPIError):
        api.worker_status(token="wrong")
    with pytest.raises(SchedulingJobAPIError) as wrong:
        api.tick(token="wrong")
    assert wrong.value.status == 403

    disabled_api, _, _ = _api(provider, token=None)
    with pytest.raises(SchedulingJobAPIError) as disabled:
        disabled_api.tick(token="anything")
    assert disabled.value.status == 404
    assert disabled.value.code == "SCHEDULING_WORKER_DISABLED"

    assert api.worker_status(token="worker-token")["worker"]["execution_mode"] == "thread"


def test_runner_refuses_unsafe_configuration():
    provider, _ = _fixture()
    service = SchedulingJobService(InMemorySchedulingJobRepository())
    with pytest.raises(SchedulingJobRunnerError) as process:
        SchedulingEngineJobRunner(service, provider=None, execution_mode="process")
    assert str(process.value) == "PROCESS_MODE_REQUIRES_PROVIDER_FACTORY"
    with pytest.raises(SchedulingJobRunnerError) as thread:
        SchedulingEngineJobRunner(service, provider=None)
    assert str(thread.value) == "THREAD_MODE_REQUIRES_PROVIDER"
    with pytest.raises(SchedulingJobRunnerError) as timeout:
        SchedulingEngineJobRunner(service, provider=provider, job_timeout=0)
    assert str(timeout.value) == "INVALID_JOB_TIMEOUT"


def test_failed_calculation_is_recorded_with_its_error_and_retry_count():

    class BrokenProvider:
        snapshot_repository = None

        def execute(self, request, *, auth_context=None):
            raise ValueError("ENGINE_REJECTED_INPUT")

    service = SchedulingJobService(InMemorySchedulingJobRepository())
    runner = SchedulingEngineJobRunner(
        service, provider=BrokenProvider()  # type: ignore[arg-type]
    )
    api = SchedulingJobAPI(service, runner=runner, worker_token="worker-token")
    job = api.submit(_scope(), snapshot_id=SNAPSHOT_ID).job

    outcome = api.tick(token="worker-token")
    assert outcome["outcome"]["failed"] == 1
    view = api.status(_scope(), job.job_id).as_dict()
    assert view["state"] == "FAILED"
    assert "ENGINE_REJECTED_INPUT" in str(view["last_error"])
    assert view["attempts"] == 1


def test_two_workers_never_execute_the_same_job_twice():
    provider, _ = _fixture()
    service = SchedulingJobService(InMemorySchedulingJobRepository())
    invocations: list[str] = []
    lock = threading.Lock()

    class CountingProvider:
        snapshot_repository = provider.snapshot_repository

        def execute(self, request, *, auth_context=None):
            with lock:
                invocations.append(request.query_id)
            time.sleep(0.02)
            return provider.execute(request, auth_context=auth_context)

    counting = CountingProvider()
    first = SchedulingEngineJobRunner(
        service,
        provider=counting,  # type: ignore[arg-type]
        owner="worker-a",
        budget=GlobalExecutionBudget(2),
        poll_interval=0.002,
    )
    second = SchedulingEngineJobRunner(
        service,
        provider=counting,  # type: ignore[arg-type]
        owner="worker-b",
        budget=GlobalExecutionBudget(2),
        poll_interval=0.002,
    )
    api = SchedulingJobAPI(
        service,
        runner=first,
        worker_token="worker-token",
        snapshot_repository=provider.snapshot_repository,
    )
    job = api.submit(_scope(), snapshot_id=SNAPSHOT_ID).job

    barrier = threading.Barrier(2)

    def drain(worker):
        barrier.wait()
        worker.drain(timeout=10)

    threads = [
        threading.Thread(target=drain, args=(first,)),
        threading.Thread(target=drain, args=(second,)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert invocations == [job.job_id]
    assert api.status(_scope(), job.job_id).as_dict()["state"] == "SUCCEEDED"


class _MutableClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 1, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now = self.now + timedelta(seconds=seconds)


def test_expired_lease_is_recovered_and_the_job_runs_once():
    provider, expected_hash = _fixture()
    clock = _MutableClock()
    service = SchedulingJobService(
        InMemorySchedulingJobRepository(),
        clock=clock,
        lease_ttl=timedelta(seconds=30),
    )
    job = service.submit(
        SchedulingJobRequest(
            tenant_id=TENANT,
            project_id=PROJECT,
            submitted_by="alice",
            request_fingerprint="fp-recovery",
            engine_version=ENGINE,
            calculation_identity=provider.snapshot_repository.get(
                BackendScope(TENANT, PROJECT, REVISION), SNAPSHOT_ID
            ).calculation_identity,
        ),
        run_parameters=(
            ("snapshot_id", SNAPSHOT_ID),
            ("project_revision", str(REVISION)),
            ("roles", '["project_admin"]'),
        ),
    ).job

    # A worker claims the job and disappears without renewing its lease.
    service.claim(
        tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, owner="dead-worker"
    )
    clock.advance(31)

    api = SchedulingJobAPI(
        service,
        runner=SchedulingEngineJobRunner(
            service,
            provider=provider,
            owner="recovered-worker",
            budget=GlobalExecutionBudget(2),
            poll_interval=0.002,
        ),
        worker_token="worker-token",
        snapshot_repository=provider.snapshot_repository,
    )
    outcome = api.tick(token="worker-token")

    assert outcome["outcome"]["claimed"] == 1
    assert outcome["outcome"]["succeeded"] == 1
    view = api.status(_scope(), job.job_id).as_dict()
    assert view["state"] == "SUCCEEDED"
    assert view["attempts"] == 2
    assert api.result_payload(_scope(), job.job_id)["result"]["output_hash"] == expected_hash


# -- process mode ----------------------------------------------------------

requires_fork = pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(),
    reason="the child must inherit the file database handle opened above",
)


def _process_provider() -> AuthoritativeScheduleQueryProvider:
    database = str(_PROCESS_STATE["database"])
    connection = sqlite3.connect(database, check_same_thread=False)
    snapshots = SQLiteScheduleInputSnapshotRepository(connection)
    contexts = SQLiteCalculationContextRepository(connection)
    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    return AuthoritativeScheduleQueryProvider(
        snapshots,
        lambda: registry,
        calculation_context_repository=contexts,
    )


class _SlowRunner(SchedulingEngineJobRunner):
    def _calculate_with_slots(self, job, slots):
        time.sleep(2)
        return super()._calculate_with_slots(job, slots)


@requires_fork
def test_process_mode_calculates_in_a_child_and_publishes_the_same_hash(tmp_path):
    database = str(tmp_path / "snapshots.sqlite3")
    provider, expected_hash = _fixture(database)
    _PROCESS_STATE["database"] = database
    try:
        service = SchedulingJobService(InMemorySchedulingJobRepository())
        cache = ScheduleResultCache(max_weight_bytes=4 * 1024 * 1024)
        runner = SchedulingEngineJobRunner(
            service,
            provider=None,
            provider_factory=_process_provider,
            execution_mode="process",
            start_method="fork",
            budget=GlobalExecutionBudget(2),
            result_cache=cache,
            poll_interval=0.002,
        )
        api = SchedulingJobAPI(
            service,
            runner=runner,
            worker_token="worker-token",
            snapshot_repository=provider.snapshot_repository,
        )
        job = api.submit(_scope(), snapshot_id=SNAPSHOT_ID).job
        outcome = api.tick(token="worker-token")

        assert outcome["outcome"]["process_starts"] == 1
        assert outcome["outcome"]["inline_fallbacks"] == 0
        assert outcome["outcome"]["succeeded"] == 1
        result = api.result_payload(_scope(), job.job_id)
        assert result["result"]["output_hash"] == expected_hash

        # A second submission over the same immutable input is served from the
        # tenant-scoped result cache instead of a second calculation.
        repeated = api.submit(_scope(), snapshot_id=SNAPSHOT_ID).job
        second = api.tick(token="worker-token")
        assert second["outcome"]["cache_hits"] == 1
        assert second["outcome"]["process_starts"] == 0
        assert (
            api.result_payload(_scope(), repeated.job_id)["result"]["output_hash"]
            == expected_hash
        )
    finally:
        _PROCESS_STATE.pop("database", None)


@requires_fork
def test_process_timeout_marks_the_job_failed(tmp_path):
    database = str(tmp_path / "snapshots.sqlite3")
    provider, _ = _fixture(database)
    _PROCESS_STATE["database"] = database
    try:
        service = SchedulingJobService(InMemorySchedulingJobRepository())
        runner = _SlowRunner(
            service,
            provider=None,
            provider_factory=_process_provider,
            execution_mode="process",
            start_method="fork",
            budget=GlobalExecutionBudget(2),
            job_timeout=0.2,
            poll_interval=0.01,
        )
        api = SchedulingJobAPI(
            service,
            runner=runner,
            worker_token="worker-token",
            snapshot_repository=provider.snapshot_repository,
        )
        job = api.submit(_scope(), snapshot_id=SNAPSHOT_ID).job
        outcome = api.tick(token="worker-token")

        assert outcome["outcome"]["succeeded"] == 0
        assert outcome["outcome"]["failed"] == 1
        view = api.status(_scope(), job.job_id).as_dict()
        assert view["state"] == "FAILED"
        assert "SCHEDULING_JOB_TIMEOUT" in str(view["last_error"])
    finally:
        _PROCESS_STATE.pop("database", None)
