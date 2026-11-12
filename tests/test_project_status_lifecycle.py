from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest

from construction_pm.application.authorization import AuthorizationError, Permission, default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleError,
    ProjectLifecycleService,
    ProjectStatusEvent,
    ProjectSummary,
    normalize_project_status,
)
from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

RPS_PROJECT = "preview-rps-01"


class _Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


class _Projects:
    def __init__(self, project: ProjectSummary) -> None:
        self.project = project
        self.events: tuple[ProjectStatusEvent, ...] = ()
        self.status_calls: list[dict[str, object]] = []

    def list_for_user(self, tenant_id, user_id):
        return (self.project,)

    def get_for_user(self, tenant_id, project_id, user_id):
        if project_id != self.project.project_id:
            return None
        return self.project

    def set_status_for_user(
        self, tenant_id, user_id, project_id, *, status, expected_revision, actor_user_id, recorded_at
    ):
        self.status_calls.append({"status": status, "expected_revision": expected_revision})
        if self.project.settings_revision != expected_revision:
            return None
        event = ProjectStatusEvent(
            tenant_id,
            project_id,
            f"{project_id}@{expected_revision + 1}",
            self.project.status,
            status,
            actor_user_id,
            recorded_at,
            expected_revision + 1,
        )
        self.events = (*self.events, event)
        self.project = ProjectSummary(
            project_id=self.project.project_id,
            tenant_id=self.project.tenant_id,
            name=self.project.name,
            revision=self.project.revision,
            status=status,
            settings_revision=expected_revision + 1,
        )
        return self.project

    def status_history_for_user(self, tenant_id, project_id, user_id):
        return self.events


def _session(role: str) -> AuthenticatedSession:
    return AuthenticatedSession(
        "s1",
        "user-1",
        "tenant-a",
        frozenset({role}),
        expires_at=__import__("datetime").datetime(2030, 1, 1, tzinfo=__import__("datetime").timezone.utc),
    )


NOW = __import__("datetime").datetime(2026, 11, 12, 9, 0, tzinfo=__import__("datetime").timezone.utc)


def _service(role: str):
    project = ProjectSummary("project-a", "tenant-a", "Project A", 7)
    projects = _Projects(project)
    service = ProjectLifecycleService(_Sessions(_session(role)), projects, default_project_policy())
    return service, projects


def test_status_is_normalized_to_the_general_tab_vocabulary():
    assert normalize_project_status("Active") == "active"
    assert normalize_project_status("WHAT-IF") == "what_if"
    assert normalize_project_status("what if") == "what_if"
    assert normalize_project_status("planned") == "planned"
    for bad in ("archived", "", None, 3):
        with pytest.raises(ProjectLifecycleError, match="PROJECT_STATUS_INVALID"):
            normalize_project_status(bad)


def test_status_change_requires_project_admin():
    service, projects = _service("viewer")
    with pytest.raises(AuthorizationError):
        service.set_project_status(
            "s1", "project-a", status="inactive", expected_revision=0, now=NOW
        )
    assert projects.status_calls == []


def test_status_change_is_revision_guarded_and_returns_the_stored_row():
    service, projects = _service("project_admin")
    updated = service.set_project_status(
        "s1", "project-a", status="planned", expected_revision=0, now=NOW
    )
    assert updated.status == "planned" and updated.settings_revision == 1
    assert projects.status_calls == [{"status": "planned", "expected_revision": 0}]
    with pytest.raises(ProjectLifecycleError, match="PROJECT_REVISION_CONFLICT"):
        service.set_project_status(
            "s1", "project-a", status="inactive", expected_revision=0, now=NOW
        )


def test_setting_the_same_status_is_an_idempotent_no_op():
    service, projects = _service("project_admin")
    current = service.set_project_status(
        "s1", "project-a", status="active", expected_revision=0, now=NOW
    )
    assert current.status == "active" and current.settings_revision == 0
    assert projects.status_calls == []


def test_status_history_requires_project_read():
    service, _ = _service("viewer")
    assert service.project_status_history("s1", "project-a", now=NOW) == ()


# --- HTTP seam over the preview runtime ---------------------------------------


def _request(app, method: str, path: str, *, payload: dict | None = None, cookie: str | None = None):
    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }
    if body:
        environ["CONTENT_TYPE"] = "application/json"
    if cookie is not None:
        environ["HTTP_COOKIE"] = f"cp_session={cookie}"
    captured: dict[str, object] = {}

    def start_response(status, response_headers) -> None:
        captured["status"] = status
        captured["headers"] = response_headers

    chunks = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), chunks


def test_preview_status_change_is_audited_and_survives_a_reopen(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        status, body = _request(runtime.app, "GET", f"/api/projects/{RPS_PROJECT}", cookie=admin.session_id)
        assert status == 200
        project = json.loads(body)["project"]
        assert project["status"] == "active" and project["settings_revision"] == 0

        status, body = _request(
            runtime.app,
            "POST",
            f"/api/projects/{RPS_PROJECT}/status",
            payload={"status": "planned", "expected_revision": 0},
            cookie=admin.session_id,
        )
        assert status == 200
        saved = json.loads(body)
        assert saved["contract_version"] == "project-status-api.v1"
        assert saved["project"]["status"] == "planned"
        assert saved["project"]["settings_revision"] == 1

        status, body = _request(
            runtime.app, "GET", f"/api/projects/{RPS_PROJECT}/status-history", cookie=admin.session_id
        )
        assert status == 200
        events = json.loads(body)["events"]
        assert len(events) == 1
        assert events[0]["from_status"] == "active" and events[0]["to_status"] == "planned"
        assert events[0]["actor_user_id"] == "preview-admin"
        assert events[0]["settings_revision"] == 1
        assert events[0]["event_id"] == f"{RPS_PROJECT}@1"
    finally:
        runtime.close()

    reopened = open_preview_runtime(tmp_path / "preview.sqlite3")
    try:
        admin = reopened.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        status, body = _request(
            reopened.app, "GET", f"/api/projects/{RPS_PROJECT}/status-history", cookie=admin.session_id
        )
        assert status == 200
        assert [event["to_status"] for event in json.loads(body)["events"]] == ["planned"]
        status, body = _request(reopened.app, "GET", f"/api/projects/{RPS_PROJECT}", cookie=admin.session_id)
        assert json.loads(body)["project"]["status"] == "planned"
    finally:
        reopened.close()


def test_preview_status_guards_permission_revision_and_vocabulary(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        status, body = _request(
            runtime.app,
            "GET",
            f"/api/projects/{RPS_PROJECT}/status-history",
            cookie=viewer.session_id,
        )
        assert status == 200 and json.loads(body)["events"] == []
        status, _ = _request(
            runtime.app,
            "POST",
            f"/api/projects/{RPS_PROJECT}/status",
            payload={"status": "inactive", "expected_revision": 0},
            cookie=viewer.session_id,
        )
        assert status == 403

        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        status, body = _request(
            runtime.app,
            "POST",
            f"/api/projects/{RPS_PROJECT}/status",
            payload={"status": "archived", "expected_revision": 0},
            cookie=admin.session_id,
        )
        assert status == 400 and json.loads(body)["code"] == "PROJECT_STATUS_INVALID"

        status, body = _request(
            runtime.app,
            "POST",
            f"/api/projects/{RPS_PROJECT}/status",
            payload={"status": "inactive", "expected_revision": 9},
            cookie=admin.session_id,
        )
        assert status == 409 and json.loads(body)["code"] == "PROJECT_REVISION_CONFLICT"
        status, body = _request(
            runtime.app,
            "POST",
            f"/api/projects/{RPS_PROJECT}/status",
            payload={"status": "active", "expected_revision": 9},
            cookie=admin.session_id,
        )
        # Setting the stored status is a no-op even when the token is stale.
        assert status == 200 and json.loads(body)["project"]["status"] == "active"
    finally:
        runtime.close()
