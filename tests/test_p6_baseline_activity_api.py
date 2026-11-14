from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_baseline_activity_api import (
    P6_BASELINE_ACTIVITY_API_VERSION,
    P6BaselineActivityAPI,
    P6BaselineActivityReadError,
)
from construction_pm.p6_baseline_activity_repository import (
    P6BaselineActivity,
    SQLiteP6BaselineActivityRepository,
)
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    SQLiteP6BaselineRepository,
)

TENANT = "tenant-a"
PROJECT = "project-a"
REVISION = 4


def scope(revision: int = REVISION) -> BackendScope:
    return BackendScope(TENANT, PROJECT, revision)


def auth(role: str = "viewer", *, tenant_id: str = TENANT):
    return AuthorizationContext(
        tenant_id=tenant_id,
        project_id=PROJECT,
        user_id="u1",
        roles=frozenset({role}),
    )


def baseline(baseline_id: str = "BL-1") -> P6Baseline:
    return P6Baseline(
        scope=scope(),
        baseline_id=baseline_id,
        name="Baseline",
        baseline_type="PRIMARY",
        source_revision=REVISION,
        created_at="2026-11-02T12:00:00+00:00",
    )


def activity(
    activity_id: str,
    *,
    start: date = date(2026, 11, 2),
    finish: date = date(2026, 11, 6),
    budgeted: str = "100",
    wbs_id: str | None = "W-1",
) -> P6BaselineActivity:
    return P6BaselineActivity(
        scope=scope(),
        baseline_id="BL-1",
        activity_id=activity_id,
        planned_start=start,
        planned_finish=finish,
        budgeted_cost=Decimal(budgeted),
        currency="USD",
        wbs_id=wbs_id,
    )


class Harness:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.baselines = SQLiteP6BaselineRepository(connection)
        self.rows = SQLiteP6BaselineActivityRepository(connection)
        self.api = P6BaselineActivityAPI(
            self.rows, self.baselines, default_project_policy()
        )

    def seed(self, *activities: P6BaselineActivity, baseline_id: str = "BL-1") -> None:
        self.baselines.upsert(baseline(baseline_id))
        if activities:
            self.rows.save_many(activities)


@pytest.fixture()
def connection():
    connection = sqlite3.connect(":memory:")
    yield connection
    connection.close()


def test_list_returns_stored_windows_in_activity_order(connection):
    harness = Harness(connection)
    harness.seed(
        activity("B", start=date(2026, 11, 4), finish=date(2026, 11, 8), budgeted="250"),
        activity("A", start=date(2026, 11, 1), finish=date(2026, 11, 3)),
    )

    payload = harness.api.list(scope(), "BL-1", auth_context=auth())

    assert payload["contract_version"] == P6_BASELINE_ACTIVITY_API_VERSION
    assert payload["kind"] == "p6_baseline_activity_list"
    assert payload["baseline_id"] == "BL-1"
    assert payload["scope"] == {
        "tenant_id": TENANT,
        "project_id": PROJECT,
        "project_revision": REVISION,
    }
    assert [row["activity_id"] for row in payload["activities"]] == ["A", "B"]
    first = payload["activities"][0]
    assert first == {
        "activity_id": "A",
        "planned_start": "2026-11-01",
        "planned_finish": "2026-11-03",
        "budgeted_cost": "100",
        "currency": "USD",
        "wbs_id": "W-1",
        "earned_value_technique": "ACTIVITY_PERCENT_COMPLETE",
    }
    assert payload["activities"][1]["budgeted_cost"] == "250"


def test_list_returns_no_rows_instead_of_inventing_windows(connection):
    harness = Harness(connection)
    harness.seed()

    payload = harness.api.list(scope(), "BL-1", auth_context=auth())
    assert payload["activities"] == []


def test_list_rejects_unknown_baseline(connection):
    harness = Harness(connection)
    harness.seed(activity("A"))

    with pytest.raises(P6BaselineActivityReadError) as error:
        harness.api.list(scope(), "BL-MISSING", auth_context=auth())
    assert str(error.value) == "BASELINE_NOT_FOUND"


@pytest.mark.parametrize("baseline_id", ["", "  ", " BL-1", "BL-1 ", "A/B"])
def test_list_rejects_invalid_baseline_identifier(connection, baseline_id):
    harness = Harness(connection)
    harness.seed(activity("A"))

    with pytest.raises(P6BaselineActivityReadError) as error:
        harness.api.list(scope(), baseline_id, auth_context=auth())
    assert str(error.value) == "BASELINE_ACTIVITY_ID_INVALID"


def test_list_requires_project_read(connection):
    harness = Harness(connection)
    harness.seed(activity("A"))

    with pytest.raises(AuthorizationError) as error:
        harness.api.list(scope(), "BL-1", auth_context=auth("guest"))
    assert "project.read" in str(error.value)

    # The same rows remain readable for a role that only holds read permission.
    payload = harness.api.list(scope(), "BL-1", auth_context=auth("viewer"))
    assert len(payload["activities"]) == 1


def test_list_rejects_cross_scope_access(connection):
    harness = Harness(connection)
    harness.seed(activity("A"))

    with pytest.raises(AuthorizationError) as error:
        harness.api.list(scope(), "BL-1", auth_context=auth(tenant_id="tenant-b"))
    assert "CROSS_SCOPE_ACCESS" in str(error.value)


# --- HTTP boundary -------------------------------------------------------


class Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str) -> AuthenticatedSession | None:
        return self.session if session_id == self.session.session_id else None


class Projects:
    def __init__(self) -> None:
        self.items = {"p1": ProjectSummary("p1", "t1", "Project One", REVISION)}

    def list_for_user(self, tenant_id: str, user_id: str):
        return tuple(self.items.values())

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        return self.items.get(project_id)

    def create_for_user(self, tenant_id, user_id, project_id, name, **_kwargs):
        project = ProjectSummary(project_id, tenant_id, name, 0)
        self.items[project_id] = project
        return project

    def update_for_user(self, tenant_id, user_id, project_id, **_kwargs):
        return self.items.get(project_id)


def routes_for(harness: Harness, *, role: str = "viewer") -> ProjectLifecycleHttpRoutes:
    now = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset({role}), now + timedelta(hours=2)
    )
    lifecycle = ProjectLifecycleAPI(
        __import__(
            "construction_pm.application.project_lifecycle",
            fromlist=["ProjectLifecycleService"],
        ).ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    )
    return ProjectLifecycleHttpRoutes(
        lifecycle,
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_baseline_activity_api=harness.api,
    )


def http_call(routes, method: str, path: str):
    return routes.handle(method, path, cookies={"cp_session": "s1"}, body=b"")


def http_harness(connection) -> Harness:
    harness = Harness(connection)
    harness.baselines.upsert(
        P6Baseline(
            scope=BackendScope("t1", "p1", REVISION),
            baseline_id="BL-HTTP",
            name="HTTP",
            baseline_type="PRIMARY",
            source_revision=REVISION,
            created_at="2026-11-02T12:00:00+00:00",
        )
    )
    harness.rows.save_many(
        (
            P6BaselineActivity(
                scope=BackendScope("t1", "p1", REVISION),
                baseline_id="BL-HTTP",
                activity_id="A",
                planned_start=date(2026, 11, 2),
                planned_finish=date(2026, 11, 6),
                budgeted_cost=Decimal("100"),
                currency="USD",
            ),
        )
    )
    return harness


def test_http_returns_stored_windows(connection):
    harness = http_harness(connection)
    routes = routes_for(harness)

    status, headers, body = http_call(
        routes, "GET", "/api/projects/p1/p6/baselines/BL-HTTP/activities"
    )

    assert status == 200, body
    assert headers["Content-Type"].startswith("application/json")
    payload = json.loads(body)
    assert payload["kind"] == "p6_baseline_activity_list"
    assert payload["contract_version"] == P6_BASELINE_ACTIVITY_API_VERSION
    assert payload["scope"]["project_revision"] == REVISION
    assert payload["activities"][0]["activity_id"] == "A"


def test_http_returns_404_for_unknown_baseline(connection):
    routes = routes_for(http_harness(connection))

    status, _, body = http_call(
        routes, "GET", "/api/projects/p1/p6/baselines/BL-NONE/activities"
    )
    assert status == 404
    assert json.loads(body)["code"] == "BASELINE_NOT_FOUND"


def test_http_returns_400_for_malformed_activity_path(connection):
    routes = routes_for(http_harness(connection))

    status, _, body = http_call(
        routes, "GET", "/api/projects/p1/p6/baselines/A/B/activities"
    )
    assert status == 400
    assert json.loads(body)["code"] == "P6_BASELINE_REQUEST_INVALID"


def test_http_returns_403_without_project_read(connection):
    routes = routes_for(http_harness(connection), role="guest")

    status, _, body = http_call(
        routes, "GET", "/api/projects/p1/p6/baselines/BL-HTTP/activities"
    )
    assert status == 403
    assert json.loads(body)["code"] == "AUTHORIZATION_PERMISSION_DENIED"
