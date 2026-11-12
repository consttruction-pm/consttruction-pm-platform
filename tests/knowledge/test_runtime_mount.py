from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from construction_pm.application.authorization import AuthorizationError, default_project_policy
from construction_pm.application.project_lifecycle import SessionError
from construction_pm.knowledge.runtime import (
    SessionProjectGateway,
    build_knowledge_runtime,
    current_session,
)


class FakeLifecycle:
    """Minimal authenticated lifecycle API used to prove the real wiring path."""

    def __init__(self) -> None:
        self.sessions = {
            "admin-session": SimpleNamespace(
                user_id="admin-1", tenant_id="tenant-1", roles=frozenset({"project_admin"})
            ),
            "planner-session": SimpleNamespace(
                user_id="planner-1", tenant_id="tenant-1", roles=frozenset({"planner"})
            ),
        }
        self.projects: dict[str, SimpleNamespace] = {}
        self.create_calls: list[dict[str, object]] = []
        self.list_calls: list[str] = []

    def get_session(self, session_id, *, now):
        session = self.sessions.get(session_id)
        if session is None:
            raise SessionError("SESSION_INVALID")
        return session

    def authorize_project(self, session_id, project_id, permission, *, now):
        if project_id not in self.projects:
            raise AuthorizationError("project access denied")
        session = self.get_session(session_id, now=now)
        if permission.value != "knowledge.read" and "project_admin" not in session.roles and "planner" not in session.roles:
            raise AuthorizationError("project write denied")
        return SimpleNamespace(project_id=project_id)

    def list_projects(self, session_id, *, now):
        self.list_calls.append(session_id)
        return SimpleNamespace(projects=list(self.projects.values()))

    def get_project(self, session_id, project_id, *, now):
        return self.projects.get(project_id)

    def create_project(
        self,
        session_id,
        project_id,
        name,
        *,
        description="",
        start_date=None,
        date_system="gregorian",
        primary_calendar_id=None,
        now=None,
    ):
        self.create_calls.append(
            {
                "session_id": session_id,
                "project_id": project_id,
                "name": name,
                "description": description,
            }
        )
        project = SimpleNamespace(
            project_id=project_id,
            tenant_id="tenant-1",
            name=name,
            description=description,
            revision=1,
            settings_revision=1,
            status="active",
            start_date=None,
            date_system=date_system,
            primary_calendar_id=primary_calendar_id,
        )
        self.projects[project_id] = project
        return SimpleNamespace(
            context=SimpleNamespace(project_id=project_id, tenant_id="tenant-1", revision=1)
        )


def delegated_app(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"delegated"]


def call(app, method, path, *, session="admin-session", body=None, query=""):
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
    }
    if session is not None:
        environ["HTTP_COOKIE"] = f"cp_session={session}"
    raw = b"" if body is None else json.dumps(body).encode("utf-8")
    environ["CONTENT_LENGTH"] = str(len(raw))
    environ["wsgi.input"] = io.BytesIO(raw)
    captured: dict[str, object] = {}

    def start_response(status, headers):
        captured["status"] = status

    result = app(environ, start_response)
    payload = None if not result or not result[0] else json.loads(result[0])
    return str(captured["status"]).split(" ", 1)[0], payload


@pytest.fixture()
def stack(tmp_path):
    lifecycle = FakeLifecycle()
    runtime = build_knowledge_runtime(
        delegated_app,
        policy=default_project_policy(),
        lifecycle_api=lifecycle,
        database=str(tmp_path / "knowledge.sqlite3"),
        clock=lambda: datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    try:
        yield SimpleNamespace(runtime=runtime, lifecycle=lifecycle)
    finally:
        runtime.close()


def test_only_knowledge_paths_are_intercepted(stack) -> None:
    captured: dict[str, object] = {}

    def start_response(status, headers):
        captured["status"] = status

    body = stack.runtime.app(
        {"REQUEST_METHOD": "GET", "PATH_INFO": "/api/activities", "QUERY_STRING": ""},
        start_response,
    )
    assert body == [b"delegated"]
    assert str(captured["status"]).split(" ", 1)[0] == "200"


def test_empty_database_still_answers_honestly(stack) -> None:
    status, payload = call(stack.runtime.app, "GET", "/api/knowledge/coverage")
    assert status == "200"
    assert payload["card_counts"]["total"] == 0
    status, payload = call(stack.runtime.app, "POST", "/api/knowledge/assistant/ask", body={"question": "How do I create a project?"})
    assert status == "200"
    assert payload["kind"] in {"knowledge_gap", "gap", "clarification"}


def test_missing_session_is_rejected(stack) -> None:
    status, payload = call(stack.runtime.app, "GET", "/api/knowledge/coverage", session=None)
    assert status == "401"
    assert payload["code"] == "SESSION_REQUIRED"


def test_request_session_does_not_leak_into_the_next_call(stack) -> None:
    status, _ = call(stack.runtime.app, "GET", "/api/knowledge/coverage", session="planner-session")
    assert status == "200"
    assert current_session() is None


def test_gateway_fails_closed_without_a_bound_session() -> None:
    gateway = SessionProjectGateway(FakeLifecycle())
    with pytest.raises(Exception) as error:
        gateway.list_projects()
    assert "SESSION_REQUIRED" in str(error.value)


def test_project_creation_runs_through_the_real_lifecycle_gateway(stack) -> None:
    lifecycle: FakeLifecycle = stack.lifecycle
    status, run = call(stack.runtime.app, "POST", "/api/knowledge/assistant/workflows", body={})
    assert status == "201"
    run_id = run["run_id"]
    version = run["version"]

    def apply(step: str, payload: dict, expected: int):
        return call(
            stack.runtime.app,
            "POST",
            f"/api/knowledge/assistant/workflows/{run_id}/steps/{step}",
            body={"payload": payload, "expected_version": expected},
        )

    status, run = apply(
        "organization",
        {"organization": "CUBI", "eps": {"code": "EPS1", "name": "Engineering"}, "discipline": "Engineering"},
        version,
    )
    assert status == "200", run
    version = run["version"]
    status, run = apply("discipline", {"discipline": "Engineering", "project_type": "EPC"}, version)
    assert status == "200", run
    version = run["version"]
    status, run = apply(
        "identity",
        {"name": "Runtime Project", "project_id": "PRJ-RUNTIME-1", "timezone": "Asia/Tehran"},
        version,
    )
    assert status == "200", run
    version = run["version"]
    status, run = apply("review", {"confirm": True}, version)
    assert status == "200", run
    version = run["version"]
    status, approval = call(
        stack.runtime.app,
        "POST",
        f"/api/knowledge/assistant/workflows/{run_id}/approve",
        body={"expected_version": version},
    )
    assert status == "200", approval
    assert approval["approval_token"]
    status, run = apply(
        "create",
        {"approval_token": approval["approval_token"]},
        approval["version"],
    )
    assert status == "200", run
    assert lifecycle.create_calls == [
        {
            "session_id": "admin-session",
            "project_id": "PRJ-RUNTIME-1",
            "name": "Runtime Project",
            "description": "",
        }
    ]
    assert run["current_step"] == "settings"


def test_each_request_uses_its_own_session_for_project_reads(stack) -> None:
    lifecycle: FakeLifecycle = stack.lifecycle
    status, run = call(stack.runtime.app, "POST", "/api/knowledge/assistant/workflows", body={}, session="planner-session")
    assert status == "201"
    status, run = call(
        stack.runtime.app,
        "POST",
        f"/api/knowledge/assistant/workflows/{run['run_id']}/steps/organization",
        body={
            "payload": {
                "organization": "CUBI",
                "eps": {"code": "EPS2", "name": "Planning"},
                "discipline": "Planning",
            },
            "expected_version": run["version"],
        },
        session="planner-session",
    )
    assert status == "200", run
    status, run = call(
        stack.runtime.app,
        "POST",
        f"/api/knowledge/assistant/workflows/{run['run_id']}/steps/discipline",
        body={"payload": {"discipline": "Planning", "project_type": "EPC"}, "expected_version": run["version"]},
        session="planner-session",
    )
    assert status == "200", run
    status, run = call(
        stack.runtime.app,
        "POST",
        f"/api/knowledge/assistant/workflows/{run['run_id']}/steps/identity",
        body={
            "payload": {"name": "Planner Project", "project_id": "PRJ-RUNTIME-2", "timezone": "UTC"},
            "expected_version": run["version"],
        },
        session="planner-session",
    )
    assert status == "200", run
    assert lifecycle.list_calls == ["planner-session"]
