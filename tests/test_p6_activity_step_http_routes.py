from __future__ import annotations

import contextlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_activity_step_api import (
    P6_ACTIVITY_STEP_READ_API_VERSION,
    P6ActivityStepReadAPI,
)
from construction_pm.p6_activity_step_repository import (
    P6ActivityStep,
    P6ActivityStepApplicationService,
    SQLiteP6ActivityStepRepository,
)

NOW = datetime(2026, 11, 12, 9, 30, tzinfo=timezone.utc)


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

    def create_for_user(self, tenant_id, user_id, project_id, name, **_):
        return ProjectSummary(project_id, tenant_id, name, 0)


class NullTransactions:
    @staticmethod
    def transaction():
        return contextlib.nullcontext()


class StubActivityMaster:
    def get(self, *_args, **_kwargs):
        return None


def build(roles: frozenset[str] = frozenset({"viewer"})):
    session = AuthenticatedSession("s1", "u1", "t1", roles, NOW + timedelta(hours=1))
    service = ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    steps_api = P6ActivityStepReadAPI(
        P6ActivityStepApplicationService(
            SQLiteP6ActivityStepRepository(sqlite3.connect(":memory:")),
            NullTransactions(),
        ),
        default_project_policy(),
    )
    router = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: NOW})(),
        p6_activity_master_api=StubActivityMaster(),
        p6_activity_step_api=steps_api,
    )
    return router, steps_api


def call(router, method, path):
    status, _, raw = router.handle(
        method, path, cookies={"cp_session": "s1"}, body=b""
    )
    return status, json.loads(raw) if raw else {}


def test_steps_route_returns_empty_list_when_none_are_stored():
    router, _ = build()
    status, body = call(router, "GET", "/api/projects/p1/p6/activities/A130/steps")
    assert status == 200
    assert body["contract_version"] == P6_ACTIVITY_STEP_READ_API_VERSION
    assert body["kind"] == "p6_activity_step_list"
    assert body["activity_id"] == "A130"
    assert body["steps"] == []


def test_steps_route_returns_stored_steps_with_scope():
    router, steps_api = build()
    steps_api.service.save(
        P6ActivityStep(
            scope=BackendScope("t1", "p1", 2),
            step_id="STEP-A130-01",
            activity_id="A130",
            sequence=1,
            description="Strip topsoil",
            weight=Decimal("25"),
        )
    )
    status, body = call(router, "GET", "/api/projects/p1/p6/activities/A130/steps")
    assert status == 200
    assert body["scope"] == {"tenant_id": "t1", "project_id": "p1", "project_revision": 2}
    assert [item["step_id"] for item in body["steps"]] == ["STEP-A130-01"]
    assert body["steps"][0]["weight"] == "25"


def test_steps_route_rejects_another_project():
    router, _ = build()
    status, body = call(router, "GET", "/api/projects/p2/p6/activities/A130/steps")
    assert status == 403
    assert body["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"


def test_steps_route_is_not_available_when_the_read_api_is_missing():
    session = AuthenticatedSession("s1", "u1", "t1", frozenset({"viewer"}), NOW + timedelta(hours=1))
    service = ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    router = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: NOW})(),
        p6_activity_master_api=StubActivityMaster(),
    )
    status, body = call(router, "GET", "/api/projects/p1/p6/activities/A130/steps")
    assert status == 503
    assert body["code"] == "P6_ACTIVITY_STEP_READ_UNAVAILABLE"
