"""HTTP routes for Gantt curtain, text and notebook attachments."""

from __future__ import annotations

import contextlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_gantt_attachment import (
    P6GanttAttachmentAPI,
    SQLiteGanttAttachmentRepository,
)

NOW = datetime(2026, 11, 19, 9, 30, tzinfo=timezone.utc)


class Sessions:
    def __init__(self, session):
        self.session = session

    def get(self, session_id):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id, user_id):
        return (ProjectSummary("p1", tenant_id, "Project One", 3),)

    def get_for_user(self, tenant_id, project_id, user_id):
        if project_id != "p1":
            return None
        return ProjectSummary("p1", tenant_id, "Project One", 3)


class StubActivityMaster:
    def get(self, *_args, **_kwargs):
        return None


def build(roles: frozenset[str] = frozenset({"planner"})):
    session = AuthenticatedSession("s1", "u1", "t1", roles, NOW + timedelta(hours=1))
    service = ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    router = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: NOW})(),
        p6_activity_master_api=StubActivityMaster(),
        p6_gantt_attachment_api=P6GanttAttachmentAPI(
            SQLiteGanttAttachmentRepository(sqlite3.connect(":memory:")),
            default_project_policy(),
        ),
    )
    return router


def call(router, method, path, payload=None):
    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    status, _, raw = router.handle(method, path, cookies={"cp_session": "s1"}, body=body)
    return status, json.loads(raw) if raw else {}


def test_attachment_crud_route_round_trip():
    router = build()
    base = "/api/projects/p1/p6/gantt/attachments"
    status, body = call(router, "POST", base, {
        "kind": "curtain", "label": "Winter", "start_date": "2027-01-01",
        "end_date": "2027-01-31", "color": "#334455",
    })
    assert status == 201
    attachment = body["attachment"]
    assert attachment["record_revision"] == 1
    status, body = call(router, "GET", base)
    assert status == 200 and len(body["attachments"]) == 1
    status, body = call(router, "PATCH", f"{base}/{attachment['attachment_id']}", {
        "kind": "curtain", "label": "Winter extended", "start_date": "2027-01-01",
        "end_date": "2027-02-10", "color": "#334455", "expected_record_revision": 1,
    })
    assert status == 200 and body["attachment"]["record_revision"] == 2
    status, body = call(router, "DELETE", f"{base}/{attachment['attachment_id']}", {"expected_record_revision": 2})
    assert status == 200
    assert call(router, "GET", base)[1]["attachments"] == []


def test_attachment_conflict_returns_409():
    router = build()
    base = "/api/projects/p1/p6/gantt/attachments"
    created = call(router, "POST", base, {
        "kind": "text", "label": "Mobilise", "activity_id": "A130",
    })[1]["attachment"]
    call(router, "PATCH", f"{base}/{created['attachment_id']}", {
        "kind": "text", "label": "Mobilise", "activity_id": "A130", "expected_record_revision": 1,
    })
    status, body = call(router, "PATCH", f"{base}/{created['attachment_id']}", {
        "kind": "text", "label": "Stale", "activity_id": "A130", "expected_record_revision": 1,
    })
    assert status == 409 and body["code"] == "REVISION_CONFLICT"


def test_viewer_cannot_write_attachments():
    router = build(frozenset({"viewer"}))
    status, _ = call(router, "POST", "/api/projects/p1/p6/gantt/attachments", {
        "kind": "text", "label": "x", "activity_id": "A130",
    })
    assert status == 403
