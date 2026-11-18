"""HTTP routes for Activity Codes, Notebook and step writes."""

from __future__ import annotations

import contextlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    default_project_policy,
)
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_activity_children import (
    P6ActivityChildrenAPI,
    SQLiteActivityChildrenRepository,
)
from construction_pm.p6_activity_step_api import (
    P6ActivityStepReadAPI,
    P6ActivityStepWriteAPI,
)
from construction_pm.p6_activity_step_repository import (
    P6ActivityStepApplicationService,
    SQLiteP6ActivityStepRepository,
)

NOW = datetime(2026, 11, 18, 9, 30, tzinfo=timezone.utc)


class Sessions:
    def __init__(self, session):
        self.session = session

    def get(self, session_id):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id, user_id):
        return (ProjectSummary("p1", tenant_id, "Project One", 2),)

    def get_for_user(self, tenant_id, project_id, user_id):
        if project_id != "p1":
            return None
        return ProjectSummary("p1", tenant_id, "Project One", 2)


class NullTransactions:
    @staticmethod
    def transaction():
        return contextlib.nullcontext()


class StubActivityMaster:
    def get(self, *_args, **_kwargs):
        return None


def build(roles: frozenset[str] = frozenset({"planner"})):
    session = AuthenticatedSession("s1", "u1", "t1", roles, NOW + timedelta(hours=1))
    service = ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    step_service = P6ActivityStepApplicationService(
        SQLiteP6ActivityStepRepository(sqlite3.connect(":memory:")), NullTransactions()
    )
    router = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: NOW})(),
        p6_activity_master_api=StubActivityMaster(),
        p6_activity_children_api=P6ActivityChildrenAPI(
            SQLiteActivityChildrenRepository(sqlite3.connect(":memory:")),
            default_project_policy(),
        ),
        p6_activity_step_write_api=P6ActivityStepWriteAPI(step_service, default_project_policy()),
        p6_activity_step_api=P6ActivityStepReadAPI(step_service, default_project_policy()),
    )
    return router


def call(router, method, path, payload=None):
    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    status, _, raw = router.handle(method, path, cookies={"cp_session": "s1"}, body=body)
    return status, json.loads(raw) if raw else {}


def test_activity_codes_crud_route_round_trip():
    router = build()
    base = "/api/projects/p1/p6/activities/A130/codes"
    status, body = call(router, "POST", base, {"code_type": "AREA", "code_value": "ZONE-1", "description": "North"})
    assert status == 201
    assignment_id = body["code"]["assignment_id"]
    status, body = call(router, "GET", base)
    assert status == 200
    assert [(item["code_type"], item["code_value"]) for item in body["codes"]] == [("AREA", "ZONE-1")]
    status, body = call(router, "DELETE", f"{base}/{assignment_id}")
    assert status == 200 and body["deleted"] is True
    assert call(router, "GET", base)[1]["codes"] == []


def test_notebook_route_round_trip_and_conflict():
    router = build()
    base = "/api/projects/p1/p6/activities/A130/notebook"
    status, body = call(router, "POST", base, {"topic_name": "Kickoff", "description": "<p>Scope</p>"})
    assert status == 201
    topic = body["topic"]
    status, body = call(
        router,
        "PATCH",
        f"{base}/{topic['topic_id']}",
        {"topic_name": "Kickoff", "description": "<p>Agreed</p>", "expected_record_revision": 1},
    )
    assert status == 200 and body["topic"]["record_revision"] == 2
    status, body = call(
        router,
        "PATCH",
        f"{base}/{topic['topic_id']}",
        {"topic_name": "Stale", "description": "x", "expected_record_revision": 1},
    )
    assert status == 409 and body["code"] == "REVISION_CONFLICT"
    status, body = call(
        router, "DELETE", f"{base}/{topic['topic_id']}", {"expected_record_revision": 2}
    )
    assert status == 200
    assert call(router, "GET", base)[1]["topics"] == []


def test_viewer_cannot_post_codes():
    router = build(frozenset({"viewer"}))
    status, body = call(
        router,
        "POST",
        "/api/projects/p1/p6/activities/A130/codes",
        {"code_type": "AREA", "code_value": "ZONE-1"},
    )
    assert status == 403


def test_step_write_routes_create_update_delete():
    router = build()
    base = "/api/projects/p1/p6/activities/A130/steps"
    status, body = call(router, "POST", base, {"description": "Excavate", "weight": "40", "percent_complete": "10"})
    assert status == 201
    step_id = body["step"]["step_id"]
    status, body = call(router, "PATCH", f"{base}/{step_id}", {"description": "Excavate and trim", "percent_complete": "60"})
    assert status == 200
    assert body["step"]["percent_complete"] == "60"
    status, body = call(router, "DELETE", f"{base}/{step_id}")
    assert status == 200 and body["deleted"] is True
    assert call(router, "GET", base)[1]["steps"] == []


def test_step_write_route_requires_planner_role():
    router = build(frozenset({"viewer"}))
    status, _ = call(
        router,
        "POST",
        "/api/projects/p1/p6/activities/A130/steps",
        {"description": "Excavate"},
    )
    assert status == 403
