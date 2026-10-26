from __future__ import annotations

import json
import sqlite3
from decimal import Decimal

import pytest

from construction_pm.activity_master_repository import (
    ActivityMaster,
    SQLiteActivityMasterRepository,
)
from construction_pm.ai_action_runtime import AIActionRuntimeContext
from construction_pm.ai_assistant_project_context import (
    AIAssistantProjectContextError,
    MAX_CONTEXT_ACTIVITIES,
    MAX_CONTEXT_JSON_BYTES,
    MAX_CONTEXT_RELATIONSHIPS,
    MAX_CONTEXT_SCHEDULE_ACTIVITIES,
    PROJECT_CONTEXT_CONTRACT_VERSION,
    PersistedProjectAssistantContextProvider,
)
from construction_pm.application.authorization import default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.relationship_master_repository import (
    RelationshipMaster,
    SQLiteRelationshipMasterRepository,
)
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import DurationUnit


def runtime_context(
    *, tenant="t1", project="p1", revision="2", roles=frozenset({"project_admin"})
):
    return AIActionRuntimeContext(
        subject_id="u1",
        tenant_id=tenant,
        project_id=project,
        project_revision_id=revision,
        roles=roles,
    )


def save_activity(
    repository,
    *,
    tenant="t1",
    project="p1",
    revision=2,
    activity_id="A-1",
    name="Excavation",
):
    repository.save(
        ActivityMaster(
            scope=BackendScope(tenant, project, revision),
            activity_id=activity_id,
            name=name,
            duration_value=Decimal("2"),
            duration_unit=DurationUnit.WORKING_DAY,
        )
    )


def save_relationship(repository, *, activity_id="R-1", predecessor="A-1", successor="A-2"):
    repository.save(
        RelationshipMaster(
            scope=BackendScope("t1", "p1", 2),
            relationship_id=activity_id,
            predecessor_id=predecessor,
            successor_id=successor,
            relationship_type=RelationshipType.FS,
        )
    )


def provider(
    connection,
    *,
    schedule_facts=None,
    relationships=True,
):
    activity_repository = SQLiteActivityMasterRepository(connection)
    relationship_repository = (
        SQLiteRelationshipMasterRepository(connection) if relationships else None
    )
    return PersistedProjectAssistantContextProvider(
        activity_repository=activity_repository,
        authorization_policy=default_project_policy(),
        relationship_repository=relationship_repository,
        schedule_facts=schedule_facts,
    )


def schedule_facts_fake(calls=None, value=None, error=None):
    def read(scope, auth):
        if calls is not None:
            calls.append((scope, auth))
        if error is not None:
            raise error
        return value

    return read


def test_project_context_reads_only_the_authorized_tenant_project_and_revision():
    connection = sqlite3.connect(":memory:")
    try:
        activities = SQLiteActivityMasterRepository(connection)
        relationships = SQLiteRelationshipMasterRepository(connection)
        save_activity(activities, activity_id="A-1", name="Excavation")
        save_activity(activities, activity_id="A-2", name="Foundation")
        save_activity(activities, project="p2", activity_id="B-1", name="Other project")
        save_activity(activities, tenant="t2", activity_id="C-1", name="Other tenant")
        save_activity(activities, revision=3, activity_id="D-1", name="Other revision")
        save_relationship(relationships, activity_id="R-1")
        save_relationship(relationships, activity_id="R-2", predecessor="A-2", successor="A-1")

        context = provider(connection).read(runtime_context())
        assert context["contract_version"] == PROJECT_CONTEXT_CONTRACT_VERSION
        assert context["project_id"] == "p1"
        assert context["project_revision"] == 2
        assert context["activities"]["total"] == 2
        assert [item["activity_id"] for item in context["activities"]["items"]] == [
            "A-1",
            "A-2",
        ]
        assert context["relationships"]["total"] == 2
        assert context["relationships"]["source_available"] is True
        serialized = json.dumps(context)
        for foreign in ("Other project", "Other tenant", "Other revision", "B-1", "C-1", "D-1"):
            assert foreign not in serialized
        assert context["schedule_calculation"] == {
            "available": False,
            "reason_code": "SCHEDULE_FACTS_NOT_CONFIGURED",
        }
    finally:
        connection.close()


def test_project_context_is_bounded_and_discloses_truncation():
    connection = sqlite3.connect(":memory:")
    try:
        activities = SQLiteActivityMasterRepository(connection)
        relationships = SQLiteRelationshipMasterRepository(connection)
        for index in range(MAX_CONTEXT_ACTIVITIES + 5):
            save_activity(
                activities,
                activity_id=f"A-{index:03d}",
                name="N" * 50,
            )
        for index in range(MAX_CONTEXT_RELATIONSHIPS + 5):
            save_relationship(
                relationships,
                activity_id=f"R-{index:03d}",
                predecessor=f"A-{index:03d}",
                successor=f"A-{index + 1:03d}",
            )
        many_facts = {
            f"A-{index:03d}": {
                "start": "2026-11-01",
                "finish": "2026-11-02",
                "duration": 1,
                "critical": index % 2 == 0,
                "early_start": "2026-11-01",
                "early_finish": "2026-11-02",
                "late_start": "2026-11-01",
                "late_finish": "2026-11-02",
                "total_float": 0,
                "free_float": 0,
            }
            for index in range(MAX_CONTEXT_SCHEDULE_ACTIVITIES + 5)
        }
        context = provider(
            connection,
            schedule_facts=schedule_facts_fake(value={
                "calculation_run_identity": "a" * 64,
                "project_finish": "2026-12-01",
                "activity_count": len(many_facts),
                "activities": many_facts,
            }),
        ).read(runtime_context())

        assert context["activities"]["total"] == MAX_CONTEXT_ACTIVITIES + 5
        assert context["activities"]["returned"] == MAX_CONTEXT_ACTIVITIES
        assert context["activities"]["truncated"] is True
        assert context["relationships"]["total"] == MAX_CONTEXT_RELATIONSHIPS + 5
        assert context["relationships"]["returned"] == MAX_CONTEXT_RELATIONSHIPS
        assert context["relationships"]["truncated"] is True
        schedule = context["schedule_calculation"]
        assert schedule["available"] is True
        assert schedule["project_finish"] == "2026-12-01"
        assert schedule["total_activities"] == MAX_CONTEXT_SCHEDULE_ACTIVITIES + 5
        assert schedule["returned"] == MAX_CONTEXT_SCHEDULE_ACTIVITIES
        assert schedule["truncated"] is True
        assert all(len(item["name"]) <= 200 for item in context["activities"]["items"])
        assert len(
            json.dumps(context, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ) <= MAX_CONTEXT_JSON_BYTES
    finally:
        connection.close()


def test_project_context_reports_missing_published_schedule_without_inventing_results():
    connection = sqlite3.connect(":memory:")
    try:
        save_activity(SQLiteActivityMasterRepository(connection))
        context = provider(
            connection,
            schedule_facts=schedule_facts_fake(value=None),
        ).read(runtime_context())
        assert context["schedule_calculation"] == {
            "available": False,
            "reason_code": "NO_PUBLISHED_SCHEDULE_SNAPSHOT",
        }
        assert "project_finish" not in context["schedule_calculation"]
    finally:
        connection.close()


def test_project_context_reports_a_stable_calculation_failure_code():
    connection = sqlite3.connect(":memory:")
    try:
        save_activity(SQLiteActivityMasterRepository(connection))
        context = provider(
            connection,
            schedule_facts=schedule_facts_fake(error=ValueError("CALCULATION_CONTEXT_NOT_FOUND")),
        ).read(runtime_context())
        assert context["schedule_calculation"]["available"] is False
        assert context["schedule_calculation"]["reason_code"] == "CALCULATION_CONTEXT_NOT_FOUND"

        sanitized = provider(
            connection,
            schedule_facts=schedule_facts_fake(
                error=ValueError("internal detail that must not leak: /secret/path")
            ),
        ).read(runtime_context())
        assert sanitized["schedule_calculation"] == {
            "available": False,
            "reason_code": "SCHEDULE_CALCULATION_UNAVAILABLE",
        }
    finally:
        connection.close()


def test_project_context_requires_read_permission_and_a_trusted_revision():
    connection = sqlite3.connect(":memory:")
    try:
        save_activity(SQLiteActivityMasterRepository(connection))
        with pytest.raises(
            AIAssistantProjectContextError,
            match="AI_ASSISTANT_PROJECT_CONTEXT_NOT_AUTHORIZED",
        ):
            provider(connection).read(runtime_context(roles=frozenset()))
        with pytest.raises(
            AIAssistantProjectContextError,
            match="AI_ASSISTANT_PROJECT_CONTEXT_SCOPE_INVALID",
        ):
            provider(connection).read(runtime_context(revision="02"))
        with pytest.raises(
            AIAssistantProjectContextError,
            match="AI_ASSISTANT_PROJECT_CONTEXT_SCOPE_INVALID",
        ):
            provider(connection).read(runtime_context(revision="not-a-revision"))
    finally:
        connection.close()


def test_project_context_passes_the_authorized_scope_to_the_shared_core_reader():
    connection = sqlite3.connect(":memory:")
    calls = []
    try:
        save_activity(SQLiteActivityMasterRepository(connection))
        provider(connection, schedule_facts=schedule_facts_fake(
            calls=calls,
            value={
                "calculation_run_identity": "b" * 64,
                "project_finish": "2026-12-01",
                "activity_count": 1,
                "activities": {"A-1": {"start": "2026-11-01", "finish": "2026-12-01"}},
            },
        )).read(runtime_context())
        scope, auth = calls[0]
        assert scope == BackendScope("t1", "p1", 2)
        assert auth.tenant_id == "t1"
        assert auth.project_id == "p1"
        assert auth.user_id == "u1"
    finally:
        connection.close()
