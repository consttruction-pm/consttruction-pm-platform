from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.application.project_lifecycle import ProjectLifecycleService
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_issue_api import P6IssueAPI
from construction_pm.p6_issue_repository import SQLiteP6IssueRepository

NOW = datetime(2026, 11, 12, 9, 30, tzinfo=timezone.utc)


class Sessions:
    def __init__(self, session): self.session = session
    def get(self, session_id): return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id, user_id):
        return (ProjectSummary("p1", tenant_id, "Project One", 2),)

    def get_for_user(self, tenant_id, project_id, user_id):
        if project_id != "p1": return None
        return ProjectSummary("p1", tenant_id, "Project One", 2)

    def create_for_user(self, tenant_id, user_id, project_id, name, **_):
        return ProjectSummary(project_id, tenant_id, name, 0)


def routes(roles: frozenset[str] = frozenset({"planner"})):
    session = AuthenticatedSession("s1", "u1", "t1", roles, NOW + timedelta(hours=1))
    service = ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    api = P6IssueAPI(SQLiteP6IssueRepository(sqlite3.connect(":memory:")), default_project_policy())
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: NOW})(),
        p6_issue_api=api,
    )


def _call(router, method, path, payload=None, roles_cookie="s1"):
    body = b"" if payload is None else json.dumps(payload).encode()
    status, _, raw = router.handle(
        method, path, cookies={"cp_session": roles_cookie}, body=body
    )
    return status, json.loads(raw) if raw else {}


def _payload(**overrides):
    payload = {
        "issue_id": "ISSUE-1",
        "title": "Late structural drawings",
        "description": "Drawing package arrived after the planned start.",
        "issue_type": "schedule",
        "status": "open",
        "priority": "high",
        "owner": "u-owner",
        "responsible_manager": "u-manager",
        "date_identified": "2026-11-01",
        "due_date": "2026-11-20",
        "wbs_id": "WBS-1",
        "activity_id": "A100",
        "document_refs": ["DOC-1"],
    }
    payload.update(overrides)
    return payload


def test_issue_http_create_read_list_and_filter() -> None:
    router = routes()
    status, created = _call(router, "POST", "/api/projects/p1/p6/issues", _payload())
    assert status == 200, created
    assert created["issue"]["issue_id"] == "ISSUE-1"
    assert created["issue"]["record_revision"] == 1
    assert created["issue"]["document_refs"] == ["DOC-1"]
    assert created["scope"]["project_revision"] == 2

    status, listed = _call(router, "GET", "/api/projects/p1/p6/issues")
    assert status == 200, listed
    assert [item["issue"]["issue_id"] for item in listed["issues"]] == ["ISSUE-1"]

    status, filtered = _call(router, "GET", "/api/projects/p1/p6/issues?priority=critical")
    assert status == 200 and filtered["issues"] == []
    status, searched = _call(router, "GET", "/api/projects/p1/p6/issues?search=drawings")
    assert status == 200 and len(searched["issues"]) == 1

    status, read = _call(router, "GET", "/api/projects/p1/p6/issues/ISSUE-1")
    assert status == 200 and read["issue"]["owner"] == "u-owner"
    status, missing = _call(router, "GET", "/api/projects/p1/p6/issues/none")
    assert status == 404 and missing["code"] == "P6_ISSUE_NOT_FOUND"


def test_issue_http_update_conflict_comment_history_and_delete() -> None:
    router = routes()
    assert _call(router, "POST", "/api/projects/p1/p6/issues", _payload())[0] == 200

    status, updated = _call(
        router, "PUT", "/api/projects/p1/p6/issues/ISSUE-1",
        _payload(priority="critical", expected_revision=1),
    )
    assert status == 200, updated
    assert updated["issue"]["record_revision"] == 2

    status, conflict = _call(
        router, "PUT", "/api/projects/p1/p6/issues/ISSUE-1",
        _payload(priority="low", expected_revision=1),
    )
    assert status == 409 and conflict["code"] == "ISSUE_REVISION_CONFLICT"

    status, commented = _call(
        router, "POST", "/api/projects/p1/p6/issues/ISSUE-1/comments",
        {"comment": "Recovery plan agreed", "expected_revision": 2},
    )
    assert status == 200 and commented["issue"]["record_revision"] == 3

    status, history = _call(router, "GET", "/api/projects/p1/p6/issues/ISSUE-1/history")
    assert status == 200
    assert [item["event"]["event_type"] for item in history["events"]] == [
        "created", "updated", "commented",
    ]
    assert history["events"][-1]["event"]["actor_id"] == "u1"

    status, stale_delete = _call(
        router, "DELETE", "/api/projects/p1/p6/issues/ISSUE-1",
        {"expected_revision": 1},
    )
    assert status == 409 and stale_delete["code"] == "ISSUE_REVISION_CONFLICT"

    status, deleted = _call(
        router, "DELETE", "/api/projects/p1/p6/issues/ISSUE-1",
        {"expected_revision": 3},
    )
    assert status == 200 and deleted["deleted"] is True
    status, _ = _call(router, "GET", "/api/projects/p1/p6/issues/ISSUE-1")
    assert status == 404
    # A deleted record is no longer addressable, and its 404 carries the same
    # public code as the record read instead of the internal repository code.
    status, missing_history = _call(router, "GET", "/api/projects/p1/p6/issues/ISSUE-1/history")
    assert status == 404 and missing_history["code"] == "P6_ISSUE_NOT_FOUND"


def test_issue_http_denies_viewer_writes() -> None:
    router = routes(frozenset({"viewer"}))
    status, denied = _call(router, "POST", "/api/projects/p1/p6/issues", _payload())
    assert status == 403
    assert "project.write" in denied["code"]
    status, listed = _call(router, "GET", "/api/projects/p1/p6/issues")
    assert status == 200 and listed["issues"] == []


def test_issue_http_rejects_invalid_payload_and_bad_filter() -> None:
    router = routes()
    status, invalid = _call(router, "POST", "/api/projects/p1/p6/issues", _payload(priority="urgent"))
    assert status == 400 and invalid["code"] == "INVALID_PRIORITY"
    status, bad_filter = _call(router, "GET", "/api/projects/p1/p6/issues?status=unknown")
    assert status == 400
