from __future__ import annotations

import io
import json

from construction_pm.enterprise_task_application import EnterpriseTaskApplicationService
from construction_pm.enterprise_task_http import EnterpriseTaskHttpMiddleware

from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

from construction_pm.application.project_lifecycle import ProjectLifecycleError, SessionError
from construction_pm.enterprise_task_repository import EnterpriseTaskNotFound, StoredEnterpriseTask

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)


class FakeLifecycle:
    def __init__(self):
        self.sessions = {"alice-session": SimpleNamespace(user_id="alice", tenant_id="tenant-a", roles=frozenset({"project_manager", "enterprise_user"}))}
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
        stored = StoredEnterpriseTask(replace(task, revision=1), 1)
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
            items = [item for item in items if item.task.project_id is None and item.task.created_by_user_id == personal_user_id]
        return tuple(items[:limit])

    def update(self, task, *, expected_revision, actor_id, occurred_at):
        stored = self.get(task.tenant_id, task.task_id)
        updated = StoredEnterpriseTask(replace(task, revision=expected_revision + 1, updated_at=occurred_at), expected_revision + 1)
        self.tasks[(task.tenant_id, task.task_id)] = updated
        return updated



def _request(app, method, path, *, body=None, cookie=True, headers=None, query=""):
    raw = b"" if body is None else json.dumps(body).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "HTTP_COOKIE": "cp_session=alice-session" if cookie else "",
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": io.BytesIO(raw),
    }
    for key, value in (headers or {}).items():
        environ["HTTP_" + key.upper().replace("-", "_")] = value
    captured = {}

    def start_response(status, response_headers):
        captured["status"] = status
        captured["headers"] = response_headers

    payload = b"".join(app(environ, start_response))
    return captured["status"], json.loads(payload)


def test_task_http_requires_session_and_serves_create_list_and_read():
    lifecycle = FakeLifecycle()
    repository = FakeRepository()
    service = EnterpriseTaskApplicationService(repository, lifecycle, clock=lambda: NOW)
    app = EnterpriseTaskHttpMiddleware(lambda environ, start: start("404 Not Found", []) or [b""], service)

    status, payload = _request(app, "GET", "/api/enterprise/tasks", cookie=False)
    assert status.startswith("401")
    assert payload["code"] == "SESSION_REQUIRED"

    status, payload = _request(
        app,
        "POST",
        "/api/enterprise/tasks",
        body={"contract_version": "cubi-enterprise-task.v1", "title": "Create task"},
        headers={"Idempotency-Key": "http-create-1"},
    )
    assert status.startswith("201")
    task_id = payload["task"]["task_id"]

    status, payload = _request(app, "GET", "/api/enterprise/tasks")
    assert status.startswith("200")
    assert [task["task_id"] for task in payload["tasks"]] == [task_id]

    status, payload = _request(app, "GET", f"/api/enterprise/tasks/{task_id}")
    assert status.startswith("200")
    assert payload["task"]["title"] == "Create task"

    status, payload = _request(
        app,
        "PATCH",
        f"/api/enterprise/tasks/{task_id}",
        body={
            "contract_version": "cubi-enterprise-task.v1",
            "expected_revision": 1,
            "status": "completed",
        },
    )
    assert status.startswith("200")
    assert payload["task"]["completed_by_user_id"] == "alice"
    assert payload["revision"] == 2


def test_task_http_rejects_missing_idempotency_key_and_contract_version():
    lifecycle = FakeLifecycle()
    service = EnterpriseTaskApplicationService(FakeRepository(), lifecycle, clock=lambda: NOW)
    app = EnterpriseTaskHttpMiddleware(lambda environ, start: [b""], service)

    status, payload = _request(
        app,
        "POST",
        "/api/enterprise/tasks",
        body={"contract_version": "cubi-enterprise-task.v1", "title": "No key"},
    )
    assert status.startswith("400")
    assert payload["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    status, payload = _request(
        app,
        "POST",
        "/api/enterprise/tasks",
        body={"title": "No version"},
        headers={"Idempotency-Key": "http-create-2"},
    )
    assert status.startswith("400")
    assert payload["code"] == "UNSUPPORTED_ENTERPRISE_TASK_CONTRACT"
