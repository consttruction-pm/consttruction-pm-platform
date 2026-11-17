"""P0-J phase 4: the real Scheduling Job path runs the authoritative engine.

The executor is engine-agnostic, so the production seam is the caller-supplied
``calculate``. This module wires that seam to the same
``AuthoritativeScheduleQueryProvider`` an HTTP request uses and verifies the
full path: submit -> immutable snapshot -> queue -> worker thread -> budget
permit -> authoritative evaluation -> immutable result -> retrieval.

The result identity is the engine's ``calculation_run_identity``, so the test
also proves that two jobs over the same snapshot publish exactly the same
calculation identity and that a different calculation identity cannot be
published at all.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone

import pytest

from construction_pm.backend_p0.authoritative_schedule_query import (
    AuthoritativeScheduleQueryProvider,
)
from construction_pm.control_intelligence.contracts import ControlScope
from construction_pm.control_intelligence.query import ScheduleQueryRequest
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
from construction_pm.scheduling_job_executor import SchedulingJobExecutor
from construction_pm.scheduling_job_lifecycle import (
    InMemorySchedulingJobRepository,
    SchedulingJobError,
    SchedulingJobRequest,
    SchedulingJobResult,
    SchedulingJobService,
    SchedulingJobState,
)

TENANT = "tenant-p0j"
PROJECT = "project-p0j"
SNAPSHOT_ID = "S-P0J"
ENGINE = "cubi-26.0.0"
CALCULATION = "calc-p0j-authoritative"


def _fixture():
    calendar = CalendarReference("CAL-1", "1")
    source = AuthoritativeScheduleInput(
        snapshot_id=SNAPSHOT_ID,
        tenant_id=TENANT,
        project_id=PROJECT,
        project_revision=4,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=calendar,
        activities=(
            Activity("A", 2),
            Activity("B", 3),
            Activity("C", 1),
        ),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id=PROJECT,
        project_version=4,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00",
        input_snapshot_id=SNAPSHOT_ID,
        tenant_id=TENANT,
    )
    # The executor calculates on worker threads, exactly like production, so the
    # test connection must allow cross-thread use (the provider still reads
    # only immutable snapshots).
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    repository = SQLiteScheduleInputSnapshotRepository(connection)
    repository.save(build_snapshot(source, context, datetime(2026, 9, 30, tzinfo=timezone.utc)))
    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    provider = AuthoritativeScheduleQueryProvider(repository, lambda: registry)
    return source, context, provider


def _request(fingerprint: str) -> SchedulingJobRequest:
    return SchedulingJobRequest(
        tenant_id=TENANT,
        project_id=PROJECT,
        submitted_by="alice",
        request_fingerprint=fingerprint,
        engine_version=ENGINE,
        calculation_identity=CALCULATION,
    )


def _query(job) -> ScheduleQueryRequest:
    return ScheduleQueryRequest(
        "Q-P0J",
        ControlScope(job.tenant_id, job.project_id, 4),
        "alice",
        "show schedule",
        constraints={"snapshot_id": SNAPSHOT_ID},
    )


def _calculate_with(provider, context, *, identity_override: str | None = None):
    expected = len(("A", "B", "C"))

    def calculate(job) -> SchedulingJobResult:
        answer = provider.execute(_query(job), calculation_context=context)
        assert answer.data["activity_count"] == expected
        return SchedulingJobResult(
            tenant_id=job.tenant_id,
            project_id=job.project_id,
            job_id=job.job_id,
            engine_version=job.engine_version,
            calculation_identity=identity_override or job.calculation_identity,
            output_hash=answer.source_refs[0].content_hash,
            payload={
                "activity_count": answer.data["activity_count"],
                "project_finish": answer.data["project_finish"],
            },
            persisted_at=datetime.now(timezone.utc),
        )

    return calculate


def test_job_path_runs_the_authoritative_snapshot_engine_end_to_end():
    source, context, provider = _fixture()
    service = SchedulingJobService(InMemorySchedulingJobRepository())
    submitted = [service.submit(_request(f"fp-{index}")) for index in range(3)]
    job_ids = [item.job.job_id for item in submitted]

    executor = SchedulingJobExecutor(
        service,
        calculate=_calculate_with(provider, context),
        owner="worker-p0j",
        budget=GlobalExecutionBudget(2),
        poll_interval=0.005,
    )
    summary = executor.run_until_idle(timeout=60)

    assert summary.claimed == 3
    assert summary.succeeded == 3
    assert summary.failed == 0
    hashes = set()
    for job_id in job_ids:
        job = service.get(
            tenant_id=TENANT, project_id=PROJECT, job_id=job_id, user_id="alice"
        )
        assert job.state is SchedulingJobState.SUCCEEDED
        result = service.get_result(
            tenant_id=TENANT, project_id=PROJECT, job_id=job_id, user_id="alice"
        )
        # The published hash is the engine's own calculation run identity, and
        # it is identical for every job over the same immutable snapshot.
        hashes.add(result.output_hash)
        assert result.payload["activity_count"] == len(source.activities)
    assert len(hashes) == 1

    # Re-submitting the same snapshot after a terminal job produces a new
    # generation and the same identity, never a re-published stale result.
    again = service.submit(_request("fp-again"))
    executor2 = SchedulingJobExecutor(
        service,
        calculate=_calculate_with(provider, context),
        owner="worker-p0j-2",
        budget=GlobalExecutionBudget(1),
        poll_interval=0.005,
    )
    executor2.run_until_idle(timeout=60)
    repeated = service.get_result(
        tenant_id=TENANT,
        project_id=PROJECT,
        job_id=again.job.job_id,
        user_id="alice",
    )
    assert repeated.output_hash in hashes


def test_job_path_is_isolated_between_tenants_and_projects():
    _, context, provider = _fixture()
    service = SchedulingJobService(InMemorySchedulingJobRepository())
    first = service.submit(_request("fp-shared")).job

    other_tenant = SchedulingJobRequest(
        tenant_id="tenant-other",
        project_id=PROJECT,
        submitted_by="bob",
        request_fingerprint="fp-shared",
        engine_version=ENGINE,
        calculation_identity=CALCULATION,
    )
    other_project = SchedulingJobRequest(
        tenant_id=TENANT,
        project_id="project-other",
        submitted_by="alice",
        request_fingerprint="fp-shared",
        engine_version=ENGINE,
        calculation_identity=CALCULATION,
    )
    second = service.submit(other_tenant).job
    third = service.submit(other_project).job

    assert len({first.job_id, second.job_id, third.job_id}) == 3
    for tenant, project in (
        ("tenant-other", PROJECT),
        (TENANT, "project-other"),
        ("tenant-missing", PROJECT),
    ):
        with pytest.raises(SchedulingJobError):
            service.get(tenant_id=tenant, project_id=project, job_id=first.job_id, user_id="alice")

    executor = SchedulingJobExecutor(
        service,
        calculate=_calculate_with(provider, context),
        owner="worker-p0j",
        budget=GlobalExecutionBudget(2),
        poll_interval=0.005,
    )
    summary = executor.run_until_idle(timeout=60)
    assert summary.succeeded == 1
    assert summary.failed == 2

    with pytest.raises(SchedulingJobError):
        service.get(
            tenant_id="tenant-other",
            project_id=PROJECT,
            job_id=first.job_id,
            user_id="bob",
        )


def test_job_result_cannot_be_published_with_a_different_calculation_identity():
    _, context, provider = _fixture()
    service = SchedulingJobService(InMemorySchedulingJobRepository())
    job = service.submit(_request("fp-identity")).job

    executor = SchedulingJobExecutor(
        service,
        calculate=_calculate_with(
            provider, context, identity_override="calc-not-the-job"
        ),
        owner="worker-p0j",
        budget=GlobalExecutionBudget(1),
        poll_interval=0.005,
    )
    summary = executor.run_until_idle(timeout=60)

    assert summary.succeeded == 0
    assert summary.failed == 1
    reloaded = service.get(
        tenant_id=TENANT, project_id=PROJECT, job_id=job.job_id, user_id="alice"
    )
    assert reloaded.state is SchedulingJobState.FAILED
    with pytest.raises(SchedulingJobError):
        service.get_result(
            tenant_id=TENANT,
            project_id=PROJECT,
            job_id=job.job_id,
            user_id="alice",
        )
