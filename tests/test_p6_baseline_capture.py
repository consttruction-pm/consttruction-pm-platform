from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest

from construction_pm.activity_master_repository import (
    ActivityMaster,
    SQLiteActivityMasterRepository,
)
from construction_pm.application.authorization import (
    AuthorizationContext,
    default_project_policy,
)
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_baseline_activity_repository import (
    SQLiteP6BaselineActivityRepository,
)
from construction_pm.p6_baseline_capture import (
    P6BaselineCaptureError,
    P6BaselineCaptureRequest,
    P6BaselineCaptureService,
    P6BaselineCapturedActivity,
    P6BaselineScheduleSnapshot,
)
from construction_pm.p6_baseline_capture_api import (
    P6_BASELINE_CAPTURE_API_VERSION,
    P6BaselineCaptureAPI,
)
from construction_pm.p6_baseline_repository import SQLiteP6BaselineRepository
from construction_pm.p6_expense_repository import (
    P6Expense,
    SQLiteP6ExpenseRepository,
)
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import (
    DEMO_USERS_BY_ROLE,
    PREVIEW_TENANT_ID,
)
from construction_pm.scheduling.evm_source import EVM_TECHNIQUE_FIFTY_FIFTY
from construction_pm.scheduling.time_duration import DurationUnit
from construction_pm.wbs_master_repository import (
    SQLiteWBSMasterRepository,
    WBSParentKind,
    WBSMaster,
)

TENANT = "tenant-a"
PROJECT = "project-a"
REVISION = 4


def scope(revision: int = REVISION) -> BackendScope:
    return BackendScope(TENANT, PROJECT, revision)


def auth(
    role: str = "planner", *, tenant_id: str = TENANT
) -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id=tenant_id,
        project_id=PROJECT,
        user_id="u1",
        roles=frozenset({role}),
    )


def fact(
    activity_id: str,
    *,
    start: date = date(2026, 11, 2),
    finish: date = date(2026, 11, 6),
    duration: str = "5",
) -> P6BaselineCapturedActivity:
    return P6BaselineCapturedActivity(
        activity_id=activity_id,
        planned_start=start,
        planned_finish=finish,
        duration=Decimal(duration),
    )


class StaticScheduleSource:
    def __init__(self, snapshot: P6BaselineScheduleSnapshot | None) -> None:
        self.snapshot = snapshot

    def latest_schedule(self, scope, *, auth_context=None):
        return self.snapshot


def schedule(*facts: P6BaselineCapturedActivity) -> P6BaselineScheduleSnapshot:
    return P6BaselineScheduleSnapshot(
        snapshot_id="snap-1",
        calculation_run_identity="calc-1",
        project_finish=date(2026, 11, 6),
        activities=facts or (fact("A"),),
    )


class Harness:
    def __init__(self, connection: sqlite3.Connection, active_scope: BackendScope | None = None) -> None:
        self.connection = connection
        self.scope = active_scope or scope()
        self.transactions = SQLiteTransactionManager(connection)
        self.baselines = SQLiteP6BaselineRepository(connection)
        self.rows = SQLiteP6BaselineActivityRepository(connection)
        self.activities = SQLiteActivityMasterRepository(connection)
        self.wbs = SQLiteWBSMasterRepository(connection)
        self.assignments = SQLiteP6ResourceAssignmentRepository(connection)
        self.expenses = SQLiteP6ExpenseRepository(connection)

    def service(
        self,
        snapshot: P6BaselineScheduleSnapshot | None,
        clock: str = "2026-11-02T12:00:00+00:00",
    ) -> P6BaselineCaptureService:
        self.schedule_source = StaticScheduleSource(snapshot)
        return P6BaselineCaptureService(
            baseline_repository=self.baselines,
            baseline_activity_repository=self.rows,
            activity_repository=self.activities,
            assignment_repository=self.assignments,
            expense_repository=self.expenses,
            schedule_source=self.schedule_source,
            transaction_manager=self.transactions,
            clock=lambda: clock,
        )

    def api(
        self,
        snapshot: P6BaselineScheduleSnapshot | None,
        clock: str = "2026-11-02T12:00:00+00:00",
    ) -> P6BaselineCaptureAPI:
        return P6BaselineCaptureAPI(
            self.service(snapshot, clock), default_project_policy()
        )

    def seed_wbs(self, wbs_id: str = "W-1") -> None:
        self.wbs.save(
            WBSMaster(
                scope=self.scope,
                wbs_id=wbs_id,
                parent_kind=WBSParentKind.PROJECT,
                parent_wbs_id=None,
                code=wbs_id,
                name=wbs_id,
                sequence_number=1,
            ),
            expected_revision=0,
        )

    def seed_activity(self, activity_id: str, *, wbs_id: str | None = None) -> None:
        self.activities.save(
            ActivityMaster(
                scope=self.scope,
                activity_id=activity_id,
                duration_value=Decimal("5"),
                duration_unit=DurationUnit.WORKING_DAY,
                wbs_id=wbs_id,
                name=activity_id,
            )
        )

    def seed_activities(self, *ids: str, wbs_id: str | None = None) -> None:
        for activity_id in ids:
            self.seed_activity(activity_id, wbs_id=wbs_id)

    def assignment(
        self,
        activity_id: str,
        cost: str | None,
        currency: str | None = "USD",
        assignment_id: str | None = None,
    ) -> None:
        self.assignments.upsert(
            P6ResourceAssignment(
                scope=self.scope,
                assignment_id=assignment_id or f"AS-{activity_id}",
                activity_id=activity_id,
                resource_id="R-1",
                planned_cost=None if cost is None else Decimal(cost),
                currency=currency,
            )
        )

    def expense(
        self,
        activity_id: str | None,
        cost: str,
        currency: str | None = "USD",
        expense_id: str = "E-1",
    ) -> None:
        self.expenses.upsert(
            P6Expense(
                scope=self.scope,
                expense_id=expense_id,
                name=expense_id,
                category="MATERIAL",
                activity_id=activity_id,
                planned_cost=Decimal(cost),
                currency=currency,
            )
        )


@pytest.fixture()
def connection():
    connection = sqlite3.connect(":memory:")
    yield connection
    connection.close()


@pytest.fixture()
def harness(connection):
    harness = Harness(connection)
    harness.seed_activities("A", "B", "C")
    harness.assignment("A", "1000")
    harness.expense("A", "500", expense_id="E-A")
    harness.assignment("B", "200")
    harness.expense(None, "900", expense_id="E-WBS")
    return harness


def request(**overrides) -> P6BaselineCaptureRequest:
    payload = {
        "baseline_id": "BL-1",
        "name": "Captured Baseline",
        "baseline_type": "PRIMARY",
        "notes": "capture",
    }
    payload.update(overrides)
    return P6BaselineCaptureRequest(**payload)


def test_capture_rolls_up_assignment_and_activity_expense_budget(harness):
    result = harness.service(
        schedule(fact("A"), fact("B"), fact("C"))
    ).capture(harness.scope, request())

    assert result.replayed is False
    assert result.currency == "USD"
    assert result.baseline.baseline_id == "BL-1"
    assert result.baseline.baseline_type == "PRIMARY"
    assert result.baseline.source_revision == REVISION
    assert result.baseline.created_at == "2026-11-02T12:00:00+00:00"
    rows = {row.activity_id: row for row in result.rows}
    assert sorted(rows) == ["A", "B", "C"]
    assert rows["A"].budgeted_cost == Decimal("1500")
    assert rows["B"].budgeted_cost == Decimal("200")
    assert rows["C"].budgeted_cost == Decimal("0")
    assert rows["A"].planned_start == date(2026, 11, 2)
    assert rows["A"].currency == "USD"
    assert result.unattributed_expense_ids == ("E-WBS",)
    assert result.budgeted_cost_total() == Decimal("1700")

    stored = harness.rows.list(harness.scope, "BL-1")
    assert stored == result.rows
    assert harness.baselines.get(harness.scope, "BL-1") == result.baseline


def test_capture_uses_explicit_currency_when_no_costs_exist(connection):
    empty = Harness(connection)
    empty.seed_activity("D")
    service = empty.service(schedule(fact("D")))
    with pytest.raises(P6BaselineCaptureError) as error:
        service.capture(empty.scope, request(baseline_id="BL-NOCUR"))
    assert str(error.value) == "BASELINE_CAPTURE_CURRENCY_REQUIRED"

    result = service.capture(
        empty.scope, request(baseline_id="BL-2", currency="EUR")
    )
    assert result.currency == "EUR"
    assert {row.currency for row in result.rows} == {"EUR"}
    assert empty.baselines.get(empty.scope, "BL-2") is not None


def test_capture_rejects_mixed_cost_currency(harness):
    harness.assignment("C", "300", currency="EUR")
    service = harness.service(schedule(fact("A"), fact("B"), fact("C")))
    with pytest.raises(P6BaselineCaptureError) as error:
        service.capture(harness.scope, request())
    assert str(error.value) == "BASELINE_CAPTURE_CURRENCY_AMBIGUOUS:EUR,USD"

    with pytest.raises(P6BaselineCaptureError) as error:
        service.capture(harness.scope, request(currency="GBP"))
    assert str(error.value) == "BASELINE_CAPTURE_CURRENCY_MISMATCH:EUR,USD"


def test_capture_excludes_zero_duration_facts_without_inventing_dates(harness):
    service = harness.service(
        schedule(
            fact("A"),
            fact(
                "B",
                start=date(2026, 11, 3),
                finish=date(2026, 11, 3),
                duration="0",
            ),
        )
    )
    result = service.capture(harness.scope, request())
    assert result.excluded_activity_ids == ("B",)
    assert [row.activity_id for row in result.rows] == ["A"]


def test_capture_rejects_when_every_fact_is_unmeasurable(harness):
    service = harness.service(
        schedule(fact("A", finish=date(2026, 11, 2), duration="0"))
    )
    with pytest.raises(P6BaselineCaptureError) as error:
        service.capture(harness.scope, request())
    assert str(error.value) == "BASELINE_CAPTURE_NO_MEASURABLE_ACTIVITIES"
    assert harness.baselines.get(harness.scope, "BL-1") is None


def test_capture_replays_the_same_target_idempotently(harness):
    service = harness.service(schedule(fact("A"), fact("B"), fact("C")))
    first = service.capture(harness.scope, request())
    second = service.capture(harness.scope, request())
    assert second.replayed is True
    assert second.rows == first.rows
    assert second.baseline == first.baseline
    assert len(harness.rows.list(harness.scope, "BL-1")) == 3


def test_capture_rejects_reused_id_with_different_metadata(harness):
    service = harness.service(schedule(fact("A"), fact("B"), fact("C")))
    service.capture(harness.scope, request())
    with pytest.raises(P6BaselineCaptureError) as error:
        service.capture(harness.scope, request(name="Other name"))
    assert str(error.value) == "BASELINE_CAPTURE_TARGET_EXISTS"


def test_capture_requires_a_published_schedule(harness):
    service = harness.service(None)
    with pytest.raises(P6BaselineCaptureError) as error:
        service.capture(harness.scope, request())
    assert str(error.value) == "BASELINE_CAPTURE_SCHEDULE_SNAPSHOT_MISSING"


def test_capture_projects_wbs_and_technique(connection):
    harness = Harness(connection)
    harness.seed_wbs("W-1")
    harness.seed_activity("A", wbs_id="W-1")
    harness.assignment("A", "100")
    result = harness.service(schedule(fact("A"))).capture(
        harness.scope,
        request(earned_value_technique=EVM_TECHNIQUE_FIFTY_FIFTY),
    )
    assert result.rows[0].wbs_id == "W-1"
    assert result.rows[0].earned_value_technique == EVM_TECHNIQUE_FIFTY_FIFTY


def test_capture_api_requires_write_permission_and_matching_scope(harness):
    api = harness.api(schedule(fact("A")))
    with pytest.raises(Exception) as error:
        api.capture(
            harness.scope,
            baseline_id="BL-1",
            name="N",
            expected_revision=REVISION,
            auth_context=auth("viewer"),
        )
    assert "authorization denied" in str(error.value)

    with pytest.raises(Exception) as error:
        api.capture(
            harness.scope,
            baseline_id="BL-1",
            name="N",
            expected_revision=REVISION,
            auth_context=auth(tenant_id="tenant-b"),
        )
    assert "CROSS_SCOPE_ACCESS" in str(error.value)


def test_capture_api_rejects_stale_revision_and_bad_contract(harness):
    api = harness.api(schedule(fact("A")))
    with pytest.raises(P6BaselineCaptureError) as error:
        api.capture(
            harness.scope,
            baseline_id="BL-1",
            name="N",
            expected_revision=REVISION + 1,
            auth_context=auth(),
        )
    assert str(error.value) == "BASELINE_CAPTURE_STALE_REVISION"

    with pytest.raises(P6BaselineCaptureError) as error:
        api.capture(
            harness.scope,
            baseline_id="BL-1",
            name="N",
            expected_revision=REVISION,
            auth_context=auth(),
            contract_version="p6-baseline-capture-api.v2",
        )
    assert str(error.value) == "BASELINE_CAPTURE_CONTRACT_VERSION_UNSUPPORTED"


def test_capture_api_returns_versioned_provenance(harness):
    result = harness.api(schedule(fact("A"), fact("B"))).capture(
        harness.scope,
        baseline_id="BL-API",
        name="API baseline",
        expected_revision=REVISION,
        auth_context=auth(),
        baseline_type="SECONDARY",
        notes="api",
        currency="USD",
    )
    assert result["contract_version"] == P6_BASELINE_CAPTURE_API_VERSION
    assert result["kind"] == "p6_baseline_capture"
    assert result["scope"] == {
        "tenant_id": TENANT,
        "project_id": PROJECT,
        "project_revision": REVISION,
    }
    assert result["baseline"]["baseline_id"] == "BL-API"
    assert result["baseline"]["baseline_type"] == "SECONDARY"
    assert result["snapshot"] == {
        "snapshot_id": "snap-1",
        "calculation_run_identity": "calc-1",
        "project_finish": "2026-11-06",
        "activity_count": 2,
    }
    assert result["counts"] == {"activities": 2, "budgeted_cost": "1700"}
    assert result["excluded_activity_ids"] == []
    assert result["unattributed_expense_ids"] == ["E-WBS"]
    assert result["replayed"] is False


# --- HTTP boundary -------------------------------------------------------


class Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str) -> AuthenticatedSession | None:
        return self.session if session_id == self.session.session_id else None


class Projects:
    def __init__(self, revision: int = REVISION) -> None:
        self.items = {"p1": ProjectSummary("p1", "t1", "Project One", revision)}

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


def http_routes(
    harness: Harness, snapshot: P6BaselineScheduleSnapshot | None
) -> ProjectLifecycleHttpRoutes:
    now = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset({"planner"}), now + timedelta(hours=2)
    )
    lifecycle = ProjectLifecycleAPI(
        __import__(
            "construction_pm.application.project_lifecycle",
            fromlist=["ProjectLifecycleService"],
        ).ProjectLifecycleService(
            Sessions(session), Projects(), default_project_policy()
        )
    )
    return ProjectLifecycleHttpRoutes(
        lifecycle,
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_baseline_capture_api=harness.api(snapshot),
    )


def http_call(routes, method: str, path: str, payload: dict | None = None):
    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    return routes.handle(method, path, cookies={"cp_session": "s1"}, body=body)


def capture_payload(**overrides) -> dict:
    payload = {
        "contract_version": P6_BASELINE_CAPTURE_API_VERSION,
        "expected_revision": REVISION,
        "baseline_id": "BL-HTTP",
        "name": "HTTP Baseline",
        "baseline_type": "PRIMARY",
    }
    payload.update(overrides)
    return payload


def test_http_capture_creates_then_replays(connection):
    active = BackendScope("t1", "p1", REVISION)
    harness = Harness(connection, active)
    harness.seed_activities("A", "B")
    harness.assignment("A", "1000")
    routes = http_routes(harness, schedule(fact("A"), fact("B")))

    status, headers, body = http_call(
        routes,
        "POST",
        "/api/projects/p1/p6/baselines/capture",
        capture_payload(),
    )
    assert status == 201, body
    assert headers["Content-Type"].startswith("application/json")
    created = json.loads(body)
    assert created["kind"] == "p6_baseline_capture"
    assert created["baseline"]["baseline_id"] == "BL-HTTP"
    assert created["scope"]["project_revision"] == REVISION
    assert harness.baselines.get(active, "BL-HTTP") is not None

    status, _, body = http_call(
        routes,
        "POST",
        "/api/projects/p1/p6/baselines/capture",
        capture_payload(),
    )
    assert status == 200, body
    assert json.loads(body)["replayed"] is True


def test_http_capture_fails_closed_on_unknown_fields_and_missing_snapshot(
    connection,
):
    harness = Harness(connection, BackendScope("t1", "p1", REVISION))
    routes = http_routes(harness, None)
    status, _, body = http_call(
        routes,
        "POST",
        "/api/projects/p1/p6/baselines/capture",
        capture_payload(unexpected=1),
    )
    assert status == 400
    assert json.loads(body)["code"] == "P6_BASELINE_CAPTURE_REQUEST_INVALID"

    status, _, body = http_call(
        routes,
        "POST",
        "/api/projects/p1/p6/baselines/capture",
        capture_payload(),
    )
    assert status == 404
    assert (
        json.loads(body)["code"]
        == "BASELINE_CAPTURE_SCHEDULE_SNAPSHOT_MISSING"
    )


def test_http_capture_rejects_stale_revision(connection):
    harness = Harness(connection, BackendScope("t1", "p1", REVISION))
    harness.seed_activity("A")
    routes = http_routes(harness, schedule(fact("A")))
    status, _, body = http_call(
        routes,
        "POST",
        "/api/projects/p1/p6/baselines/capture",
        capture_payload(expected_revision=REVISION + 1),
    )
    assert status == 409
    assert json.loads(body)["code"] == "BASELINE_CAPTURE_STALE_REVISION"


# --- Preview end-to-end --------------------------------------------------


RPS_PROJECT = "preview-rps-01"


def _revision(runtime) -> int:
    summaries = runtime.store.project_rows()
    return next(
        int(item["revision"])
        for item in summaries
        if item["project_id"] == RPS_PROJECT
    )


def wsgi_call(app, method: str, path: str, *, body: bytes = b"", cookie: str | None = None):
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

    chunks = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), chunks


def test_preview_capture_feeds_the_evm_read_model(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        revision = _revision(runtime)
        active = BackendScope(PREVIEW_TENANT_ID, RPS_PROJECT, revision)
        SQLiteP6ExpenseRepository(runtime.connection).upsert(
            P6Expense(
                scope=active,
                expense_id="E-CAPTURE-1",
                name="A100 budget",
                category="LABOR",
                activity_id="A130",
                planned_cost=Decimal("1000"),
                currency="USD",
            )
        )
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        capture_path = f"/api/projects/{RPS_PROJECT}/p6/baselines/capture"
        status, body = wsgi_call(
            runtime.app,
            "POST",
            capture_path,
            cookie=planner.session_id,
            body=json.dumps(
                {
                    "contract_version": P6_BASELINE_CAPTURE_API_VERSION,
                    "expected_revision": revision,
                    "baseline_id": "BL-CAPTURE",
                    "name": "Captured schedule",
                    "baseline_type": "PRIMARY",
                    "currency": "USD",
                }
            ).encode(),
        )
        assert status == 201, body[:800]
        captured = json.loads(body)
        assert captured["contract_version"] == P6_BASELINE_CAPTURE_API_VERSION
        assert captured["snapshot"]["snapshot_id"]
        assert captured["counts"]["activities"] > 0
        assert captured["currency"] == "USD"

        status, body = wsgi_call(
            runtime.app,
            "POST",
            f"/api/projects/{RPS_PROJECT}/p6/earned-value",
            cookie=planner.session_id,
            body=json.dumps(
                {
                    "contract_version": "p6-earned-value-read-model.v1",
                    "baseline_id": "BL-CAPTURE",
                    "data_date": "2026-10-12",
                    "currency": "USD",
                    "etc_method": "PF_ONE",
                }
            ).encode(),
        )
        assert status == 200, body[:800]
        measured = json.loads(body)
        assert measured["baseline_id"] == "BL-CAPTURE"
        assert measured["earned_value"]["budget_at_completion"] == "1000"
        assert measured["earned_value"]["planned_value"]
    finally:
        runtime.close()
