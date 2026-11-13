from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_baseline_activity_repository import (
    P6BaselineActivity,
    SQLiteP6BaselineActivityRepository,
)
from construction_pm.p6_baseline_api import P6BaselineAPI
from construction_pm.p6_baseline_assignment import (
    P6BaselineAssignmentService,
    SQLiteP6BaselineRoleAssignmentRepository,
)
from construction_pm.p6_baseline_assignment_api import P6BaselineAssignmentAPI
from construction_pm.p6_baseline_conversion import P6BaselineConversionService
from construction_pm.p6_baseline_conversion_api import P6BaselineConversionAPI
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    P6BaselineApplicationService,
    SQLiteP6BaselineRepository,
)
from construction_pm.p6_current_activity_value_repository import (
    P6CurrentActivityApplicationService,
    P6CurrentActivityValue,
    SQLiteP6CurrentActivityRepository,
)

NOW = datetime(2026, 11, 3, tzinfo=timezone.utc)


class Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def __init__(self) -> None:
        self.items = {
            "p1": ProjectSummary("p1", "t1", "Target Project", 2),
            "p2": ProjectSummary("p2", "t1", "Source Project", 4),
        }

    def list_for_user(self, tenant_id: str, user_id: str):
        return tuple(
            ProjectSummary(
                p.project_id, tenant_id, p.name, p.revision,
            )
            for p in self.items.values()
        )

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        project = self.items.get(project_id)
        if project is None:
            return None
        return ProjectSummary(
            project.project_id, tenant_id, project.name, project.revision
        )


class Harness:
    def __init__(self, roles=frozenset({"project_admin"})) -> None:
        session = AuthenticatedSession("s1", "u1", "t1", roles, NOW + timedelta(hours=1))
        service = ProjectLifecycleService(
            Sessions(session), Projects(), default_project_policy()
        )
        self.lifecycle = ProjectLifecycleAPI(service)
        self.connection = sqlite3.connect(":memory:")
        self.transactions = SQLiteTransactionManager(self.connection)
        self.baselines = SQLiteP6BaselineRepository(self.connection)
        self.baseline_activities = SQLiteP6BaselineActivityRepository(self.connection)
        self.current_values = SQLiteP6CurrentActivityRepository(self.connection)
        current_service = P6CurrentActivityApplicationService(
            self.current_values, self.transactions
        )
        self.assignments = SQLiteP6BaselineRoleAssignmentRepository(self.connection)
        policy = default_project_policy()
        self.routes = ProjectLifecycleHttpRoutes(
            self.lifecycle,
            clock=type("Clock", (), {"now": lambda self: NOW})(),
            p6_baseline_api=P6BaselineAPI(
                P6BaselineApplicationService(self.baselines, self.transactions),
                policy,
            ),
            p6_baseline_assignment_api=P6BaselineAssignmentAPI(
                P6BaselineAssignmentService(
                    repository=self.assignments,
                    baseline_repository=self.baselines,
                    baseline_activity_repository=self.baseline_activities,
                    transaction_manager=self.transactions,
                ),
                policy,
            ),
            p6_baseline_conversion_api=P6BaselineConversionAPI(
                P6BaselineConversionService(
                    baseline_repository=self.baselines,
                    baseline_activity_repository=self.baseline_activities,
                    current_source=current_service,
                    transaction_manager=self.transactions,
                ),
                policy,
            ),
        )

    def seed(self) -> None:
        target = BackendScope("t1", "p1", 2)
        source = BackendScope("t1", "p2", 4)
        self.baselines.upsert(
            P6Baseline(
                target, "B-1", "Existing Target Baseline", "USER_SELECTED", 2,
                "2026-11-01T09:00:00Z",
            )
        )
        self.baseline_activities.save_many(
            (
                P6BaselineActivity(
                    target, "B-1", "A", date(2026, 11, 2), date(2026, 11, 6),
                    Decimal("1000"), "USD", "W-1",
                ),
            )
        )
        self.current_values.save_many(
            (
                P6CurrentActivityValue(
                    source, "A", date(2026, 11, 2), date(2026, 11, 6),
                    Decimal("1000"), "USD", "W-1",
                ),
                P6CurrentActivityValue(
                    source, "B", date(2026, 11, 9), date(2026, 11, 13),
                    Decimal("2500"), "EUR", "W-2",
                ),
            )
        )

    def request(self, method: str, path: str, payload: dict | None = None):
        body = b"" if payload is None else json.dumps(payload).encode()
        return self.routes.handle(
            method, path, cookies={"cp_session": "s1"}, body=body
        )


def test_role_assignment_and_summary_routes_use_authenticated_scope():
    harness = Harness()
    harness.seed()
    status, _, raw = harness.request(
        "POST",
        "/api/projects/p1/p6/baselines/B-1/assign",
        {"role": "PRIMARY", "expected_revision": 2, "replace": False},
    )
    assert status == 200
    assigned = json.loads(raw)
    assert assigned["contract_version"] == "p6-baseline-assignment-api.v1"
    assert assigned["assignment"]["baseline_id"] == "B-1"
    assert assigned["assignment"]["assigned_by"] == "u1"
    assert assigned["replaced"] is False

    status, _, raw = harness.request(
        "GET", "/api/projects/p1/p6/baselines/summary"
    )
    assert status == 200
    summary = json.loads(raw)
    assert summary["roles"]["PRIMARY"]["baseline_id"] == "B-1"
    assert summary["roles"]["PRIMARY"]["activity_count"] == 1
    assert summary["roles"]["PROJECT"] is None

    status, _, raw = harness.request(
        "GET", "/api/projects/p1/p6/baselines/roles/PRIMARY/history"
    )
    assert status == 200
    assert [row["baseline_id"] for row in json.loads(raw)["history"]] == ["B-1"]

    status, _, raw = harness.request(
        "POST",
        "/api/projects/p1/p6/baselines/B-1/assign",
        {"role": "PRIMARY", "expected_revision": 2},
    )
    assert status == 200
    assert json.loads(raw)["replaced"] is False

    status, _, raw = harness.request(
        "POST",
        "/api/projects/p1/p6/baselines/B-1/assign",
        {"role": "FOURTH", "expected_revision": 2},
    )
    assert status == 400
    assert json.loads(raw)["code"] == "INVALID_BASELINE_ROLE"

    status, _, raw = harness.request(
        "POST",
        "/api/projects/p1/p6/baselines/missing/assign",
        {"role": "PRIMARY", "expected_revision": 2},
    )
    assert status == 404
    assert json.loads(raw)["code"] == "BASELINE_NOT_FOUND"

    status, _, raw = harness.request(
        "POST",
        "/api/projects/p1/p6/baselines/B-1/assign",
        {"role": "PRIMARY", "expected_revision": 1},
    )
    assert status == 400
    assert json.loads(raw)["code"] == "BASELINE_ASSIGNMENT_STALE_REVISION"


def test_conversion_route_reads_source_project_and_is_replayable():
    harness = Harness()
    harness.seed()
    payload = {
        "source_project_id": "p2",
        "source_baseline_id": None,
        "target_baseline_id": "C-1",
        "name": "Converted From P2",
        "baseline_type": "SECONDARY",
        "expected_revision": 2,
    }
    status, _, raw = harness.request(
        "POST", "/api/projects/p1/p6/baselines/convert", payload
    )
    assert status == 201
    converted = json.loads(raw)
    assert converted["contract_version"] == "p6-baseline-conversion-api.v1"
    assert converted["source_scope"]["project_id"] == "p2"
    assert converted["source_scope"]["project_revision"] == 4
    assert converted["target_scope"]["project_id"] == "p1"
    assert converted["baseline"]["baseline_id"] == "C-1"
    assert converted["activity_count"] == 2
    assert converted["currencies"] == [
        {"currency": "EUR", "activity_count": 1, "total_budget": "2500"},
        {"currency": "USD", "activity_count": 1, "total_budget": "1000"},
    ]

    status, _, raw = harness.request(
        "POST", "/api/projects/p1/p6/baselines/convert", payload
    )
    assert status == 200
    assert json.loads(raw)["replayed"] is True

    status, _, raw = harness.request(
        "POST",
        "/api/projects/p1/p6/baselines/C-1/assign",
        {"role": "PROJECT", "expected_revision": 2},
    )
    assert status == 200
    assert json.loads(raw)["assignment"]["baseline_id"] == "C-1"

    status, _, raw = harness.request(
        "GET", "/api/projects/p1/p6/baselines/summary"
    )
    summary = json.loads(raw)
    assert summary["roles"]["PROJECT"]["baseline_id"] == "C-1"
    assert summary["roles"]["PROJECT"]["activity_count"] == 2


def test_conversion_route_rejects_same_project_and_inaccessible_source():
    harness = Harness()
    harness.seed()
    status, _, raw = harness.request(
        "POST",
        "/api/projects/p1/p6/baselines/convert",
        {
            "source_project_id": "p1",
            "target_baseline_id": "X",
            "name": "X",
            "expected_revision": 2,
        },
    )
    assert status == 400
    assert json.loads(raw)["code"] == "BASELINE_CONVERSION_SAME_PROJECT"

    status, _, raw = harness.request(
        "POST",
        "/api/projects/p1/p6/baselines/convert",
        {
            "source_project_id": "unknown",
            "target_baseline_id": "X",
            "name": "X",
            "expected_revision": 2,
        },
    )
    assert status == 403
    assert json.loads(raw)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"


def test_viewer_can_read_summary_but_cannot_assign_or_convert():
    harness = Harness(roles=frozenset({"viewer"}))
    harness.seed()
    status, _, _ = harness.request(
        "GET", "/api/projects/p1/p6/baselines/summary"
    )
    assert status == 200

    status, _, raw = harness.request(
        "POST",
        "/api/projects/p1/p6/baselines/B-1/assign",
        {"role": "PRIMARY", "expected_revision": 2},
    )
    assert status == 403
    assert "AUTHORIZATION_PERMISSION_DENIED" in json.loads(raw)["code"]

    status, _, raw = harness.request(
        "POST",
        "/api/projects/p1/p6/baselines/convert",
        {
            "source_project_id": "p2",
            "target_baseline_id": "X",
            "name": "X",
            "expected_revision": 2,
        },
    )
    assert status == 403
    assert "AUTHORIZATION_PERMISSION_DENIED" in json.loads(raw)["code"]
