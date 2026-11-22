from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from construction_pm.application.authorization import Permission
from construction_pm.application.project_lifecycle import ProjectLifecycleError, SessionError
from construction_pm.enterprise_task_application import (
    EnterpriseTaskApplicationService,
    EnterpriseTaskAuthorizationError,
)
from construction_pm.enterprise_task_repository import (
    EnterpriseTaskNotFound,
    StoredEnterpriseTask,
)

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)


class FakeLifecycle:
    def __init__(self):
        self.sessions = {
            "alice-session": SimpleNamespace(user_id="alice", tenant_id="tenant-a", roles=frozenset({"project_manager", "enterprise_user"})),
            "bob-session": SimpleNamespace(user_id="bob", tenant_id="tenant-a", roles=frozenset({"viewer", "enterprise_viewer"})),
        }
        self.grants = set()

    def get_session(self, session_id, *, now):
        if session_id not in self.sessions:
            raise SessionError("SESSION_INVALID")
        return self.sessions[session_id]

    def authorize_project(self, session_id, project_id, permission, *, now):
        if (session_id, project_id, permission) not in self.grants:
            raise ProjectLifecycleError("PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED")
        session = self.sessions[session_id]
        return SimpleNamespace(context=SimpleNamespace(tenant_id=session.tenant_id, project_id=project_id))


class FakeRepository:
    def __init__(self):
        self.tasks = {}
        self.idempotency = {}

    def create(self, task, *, idempotency_key, actor_id, occurred_at):
        key = (task.tenant_id, idempotency_key)
        if key in self.idempotency:
            return self.idempotency[key]
        stored_task = replace(task, revision=1)
        stored = StoredEnterpriseTask(stored_task, 1)
        self.tasks[(task.tenant_id, task.task_id)] = stored
        self.idempotency[key] = stored
        return stored

    def get(self, tenant_id, task_id):
        stored = self.tasks.get((tenant_id, task_id))
        if stored is None:
            raise EnterpriseTaskNotFound("ENTERPRISE_TASK_NOT_FOUND")
        return stored

    def list_for_tenant(self, tenant_id, *, limit=100, before_updated_at=None, before_task_id=None, project_id=None, personal_user_id=None):
        items = [stored for (tenant, _), stored in self.tasks.items() if tenant == tenant_id]
        if project_id is not None:
            items = [item for item in items if item.task.project_id == project_id]
        elif personal_user_id is not None:
            items = [
                item for item in items
                if item.task.project_id is None
                and (item.task.created_by_user_id == personal_user_id or item.task.assigned_user_id == personal_user_id)
            ]
        items.sort(key=lambda item: (item.task.updated_at is None, -(item.task.updated_at.timestamp()) if item.task.updated_at else 0, item.task.task_id))
        return tuple(items[:limit])

    def update(self, task, *, expected_revision, actor_id, occurred_at):
        current = self.get(task.tenant_id, task.task_id)
        if current.revision != expected_revision:
            raise EnterpriseTaskRevisionConflict("ENTERPRISE_TASK_REVISION_CONFLICT")
        stored_task = replace(task, revision=expected_revision + 1, updated_at=occurred_at)
        stored = StoredEnterpriseTask(stored_task, expected_revision + 1)
        self.tasks[(task.tenant_id, task.task_id)] = stored
        return stored


@pytest.fixture
def service():
    return EnterpriseTaskApplicationService(
        FakeRepository(),
        FakeLifecycle(),
        clock=lambda: NOW,
    )


def test_personal_task_identity_is_derived_from_authenticated_session(service):
    stored = service.create_task(
        "alice-session",
        {
            "title": "Prepare weekly report",
            "created_by_user_id": "forged-user",
            "tenant_id": "forged-tenant",
            "contract_version": "cubi-enterprise-task.v1",
        },
        idempotency_key="personal-create-1",
    )
    assert stored.task.created_by_user_id == "alice"
    assert stored.task.tenant_id == "tenant-a"
    assert stored.task.assigned_user_id == "alice"
    assert [item.task.task_id for item in service.list_tasks("alice-session")] == [stored.task.task_id]
    with pytest.raises(EnterpriseTaskNotFound):
        service.get_task("bob-session", stored.task.task_id)


def test_project_task_requires_project_write_and_updates_completion_actor(service):
    lifecycle = service._lifecycle
    with pytest.raises(EnterpriseTaskAuthorizationError):
        service.create_task(
            "alice-session",
            {"title": "Review submittal", "project_id": "project-1"},
            idempotency_key="project-create-denied",
        )
    lifecycle.grants.add(("alice-session", "project-1", Permission.PROJECT_WRITE))
    lifecycle.grants.add(("alice-session", "project-1", Permission.PROJECT_READ))
    created = service.create_task(
        "alice-session",
        {"title": "Review submittal", "project_id": "project-1"},
        idempotency_key="project-create-1",
    )
    with pytest.raises(EnterpriseTaskNotFound):
        service.get_task("bob-session", created.task.task_id)
    updated = service.update_task(
        "alice-session",
        created.task.task_id,
        {"expected_revision": 1, "status": "completed"},
    )
    assert updated.revision == 2
    assert updated.task.completed_by_user_id == "alice"
    assert updated.task.status.value == "completed"


def test_team_assignment_and_cross_user_personal_assignment_fail_closed(service):
    with pytest.raises(ValueError, match="TEAM_ASSIGNMENT_NOT_AVAILABLE"):
        service.create_task(
            "alice-session",
            {"title": "Team task", "assigned_team_id": "team-1"},
            idempotency_key="team-create",
        )
    with pytest.raises(EnterpriseTaskAuthorizationError):
        service.create_task(
            "alice-session",
            {"title": "Other user's task", "assigned_user_id": "bob"},
            idempotency_key="personal-cross-user",
        )


def test_idempotent_create_retry_returns_original_task(service):
    first = service.create_task(
        "alice-session",
        {"title": "Same request"},
        idempotency_key="retry-key",
    )
    second = service.create_task(
        "alice-session",
        {"title": "Same request"},
        idempotency_key="retry-key",
    )
    assert second == first


def test_enterprise_access_requires_explicit_session_entitlement(service):
    service._lifecycle.sessions["unentitled-session"] = SimpleNamespace(
        user_id="unentitled",
        tenant_id="tenant-a",
        roles=frozenset({"project_admin"}),
    )
    with pytest.raises(EnterpriseTaskAuthorizationError, match="ENTERPRISE_ACCESS_DENIED"):
        service.list_tasks("unentitled-session")
    with pytest.raises(EnterpriseTaskAuthorizationError, match="ENTERPRISE_ACCESS_DENIED"):
        service.create_task(
            "unentitled-session",
            {"title": "Must not enter Enterprise"},
            idempotency_key="unentitled-create",
        )


def test_platform_owner_can_read_and_write_enterprise_tasks(service):
    service._lifecycle.sessions["owner-session"] = SimpleNamespace(
        user_id="owner",
        tenant_id="tenant-a",
        roles=frozenset({"global_admin"}),
    )
    stored = service.create_task(
        "owner-session",
        {"title": "Owner enters Enterprise"},
        idempotency_key="owner-create-1",
    )
    assert stored.task.created_by_user_id == "owner"
    assert [item.task.task_id for item in service.list_tasks("owner-session")] == [
        stored.task.task_id
    ]


def test_enterprise_viewer_can_read_but_cannot_write_personal_tasks(service):
    with pytest.raises(EnterpriseTaskAuthorizationError, match="ENTERPRISE_WRITE_DENIED"):
        service.create_task(
            "bob-session",
            {"title": "Read-only role cannot create"},
            idempotency_key="viewer-create",
        )
