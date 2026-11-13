from __future__ import annotations

import json
import sqlite3
import threading
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

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
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_baseline_activity_repository import (
    P6BaselineActivity,
    SQLiteP6BaselineActivityRepository,
)
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    SQLiteP6BaselineRepository,
)
from construction_pm.p6_baseline_update import (
    BASELINE_UPDATE_FIELDS,
    P6BaselineUpdateSelection,
    P6BaselineUpdateService,
)
from construction_pm.p6_baseline_update_api import (
    BASELINE_VARIANCE_CONVENTION,
    P6_BASELINE_UPDATE_API_VERSION,
    P6BaselineUpdateAPI,
)
from construction_pm.p6_current_activity_value_repository import (
    P6CurrentActivityApplicationService,
    P6CurrentActivityPersistenceError,
    P6CurrentActivityValue,
    SQLiteP6CurrentActivityRepository,
)
from construction_pm.scheduling.evm_source import (
    EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
    EVM_TECHNIQUE_FIFTY_FIFTY,
)


TENANT = "tenant-a"
PROJECT = "project-a"
REVISION = 7


def scope(revision: int = REVISION) -> BackendScope:
    return BackendScope(TENANT, PROJECT, revision)


def auth(
    *,
    tenant_id: str = TENANT,
    project_id: str = PROJECT,
    role: str = "planner",
) -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id=tenant_id,
        project_id=project_id,
        user_id="u1",
        roles=frozenset({role}),
    )


def baseline_row(
    activity_id: str,
    *,
    baseline_id: str = "B-1",
    s: BackendScope | None = None,
    start: date = date(2026, 11, 2),
    finish: date = date(2026, 11, 6),
    budget: str = "1000",
    currency: str = "USD",
    wbs_id: str | None = "W-1",
    technique: str = EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
) -> P6BaselineActivity:
    return P6BaselineActivity(
        scope=s or scope(),
        baseline_id=baseline_id,
        activity_id=activity_id,
        planned_start=start,
        planned_finish=finish,
        budgeted_cost=Decimal(budget),
        currency=currency,
        wbs_id=wbs_id,
        earned_value_technique=technique,
    )


def current_value(
    activity_id: str,
    *,
    s: BackendScope | None = None,
    start: date = date(2026, 11, 2),
    finish: date = date(2026, 11, 6),
    budget: str = "1000",
    currency: str = "USD",
    wbs_id: str | None = "W-1",
    technique: str = EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
) -> P6CurrentActivityValue:
    return P6CurrentActivityValue(
        scope=s or scope(),
        activity_id=activity_id,
        planned_start=start,
        planned_finish=finish,
        budgeted_cost=Decimal(budget),
        currency=currency,
        wbs_id=wbs_id,
        earned_value_technique=technique,
    )


class Harness:
    def __init__(self, connection: sqlite3.Connection, *, clock: str | None = None):
        self.connection = connection
        self.transaction_manager = SQLiteTransactionManager(connection)
        self.baselines = SQLiteP6BaselineRepository(connection)
        self.activities = SQLiteP6BaselineActivityRepository(connection)
        self.current_values = SQLiteP6CurrentActivityRepository(connection)
        self.current_service = P6CurrentActivityApplicationService(
            self.current_values, self.transaction_manager
        )
        self.service = P6BaselineUpdateService(
            repository=self.activities,
            transaction_manager=self.transaction_manager,
            baseline_repository=self.baselines,
            current_source=self.current_service,
            clock=lambda: clock or "2026-11-02T12:00:00+00:00",
        )
        self.api = P6BaselineUpdateAPI(
            self.service, default_project_policy()
        )

    def seed(
        self,
        baseline_rows,
        current_rows,
        *,
        baseline_id: str = "B-1",
        s: BackendScope | None = None,
    ) -> None:
        active_scope = s or scope()
        if baseline_rows:
            self.baselines.upsert(
                P6Baseline(
                    active_scope,
                    baseline_id,
                    "Approved Baseline",
                    "PRIMARY",
                    active_scope.project_revision,
                    "2026-11-01T09:00:00Z",
                )
            )
            self.activities.save_many(baseline_rows)
        if current_rows:
            self.current_service.save_many(current_rows)


@pytest.fixture()
def connection():
    connection = sqlite3.connect(":memory:")
    yield connection
    connection.close()


@pytest.fixture()
def harness(connection):
    harness = Harness(connection)
    source = (
        baseline_row("A"),
        baseline_row("B", budget="200"),
        baseline_row("D", budget="400"),
    )
    current = (
        current_value(
            "A",
            start=date(2026, 11, 4),
            finish=date(2026, 11, 10),
            budget="1250",
            wbs_id="W-2",
            technique=EVM_TECHNIQUE_FIFTY_FIFTY,
        ),
        current_value("B", budget="200"),
        current_value("C", budget="300"),
    )
    harness.seed(source, current)
    return harness


def test_preview_reads_persisted_baseline_and_current_state_without_writing(harness):
    result = harness.api.preview(
        scope(),
        "B-1",
        "B-2",
        P6BaselineUpdateSelection(),
        expected_revision=REVISION,
        auth_context=auth(),
    )

    assert result["contract_version"] == P6_BASELINE_UPDATE_API_VERSION
    assert result["kind"] == "p6_baseline_update_preview"
    assert result["source_baseline_id"] == "B-1"
    assert result["target_baseline_id"] == "B-2"
    assert result["counts"] == {
        "added": 1,
        "updated": 1,
        "removed": 0,
        "unchanged": 2,
        "total": 4,
    }
    assert result["added_activity_ids"] == ["C"]
    assert result["updated_activity_ids"] == ["A"]
    assert result["removed_activity_ids"] == []
    assert result["unchanged_activity_ids"] == ["B", "D"]

    changes = {row["activity_id"]: row for row in result["changes"]}
    assert changes["A"]["change_type"] == "CHANGED"
    assert changes["A"]["fields"]["planned_finish"] == {
        "baseline": "2026-11-06",
        "current": "2026-11-10",
        "proposed": "2026-11-10",
    }
    assert changes["A"]["fields"]["budgeted_cost"] == {
        "baseline": "1000",
        "current": "1250",
        "proposed": "1250",
    }
    assert changes["C"]["change_type"] == "ADDED"
    assert changes["B"]["change_type"] == "UNCHANGED"

    # Preview never creates the target baseline or its rows.
    assert harness.baselines.get(scope(), "B-2") is None
    assert harness.activities.list(scope(), "B-2") == ()
    # The source baseline is equally untouched.
    stored = harness.activities.list(scope(), "B-1")
    assert [(row.activity_id, row.budgeted_cost) for row in stored] == [
        ("A", Decimal("1000")),
        ("B", Decimal("200")),
        ("D", Decimal("400")),
    ]


def test_preview_selection_limits_activities_and_fields(harness):
    result = harness.api.preview(
        scope(),
        "B-1",
        "B-2",
        P6BaselineUpdateSelection(
            activity_ids=frozenset({"A"}),
            fields=frozenset({"budgeted_cost"}),
        ),
        expected_revision=REVISION,
        auth_context=auth(),
    )

    assert result["updated_activity_ids"] == ["A"]
    assert result["added_activity_ids"] == []
    assert set(result["unchanged_activity_ids"]) == {"B", "D"}
    changes = {row["activity_id"]: row for row in result["changes"]}
    assert changes["A"]["fields"] == {
        "budgeted_cost": {
            "baseline": "1000",
            "current": "1250",
            "proposed": "1250",
        }
    }
    # A field excluded from the selection keeps its baseline value.
    assert changes["A"]["fields"].get("planned_finish") is None


def test_apply_creates_an_immutable_target_baseline_and_preserves_the_source(harness):
    result = harness.api.apply(
        scope(),
        "B-1",
        "B-2",
        P6BaselineUpdateSelection(
            fields=frozenset({"planned_finish", "budgeted_cost"})
        ),
        target_name="Updated Baseline",
        expected_revision=REVISION,
        auth_context=auth(),
    )

    assert result["kind"] == "p6_baseline_update_apply"
    assert result["baseline"]["baseline_id"] == "B-2"
    assert result["baseline"]["name"] == "Updated Baseline"
    assert result["baseline"]["baseline_type"] == "USER_SELECTED"
    assert result["baseline"]["source_revision"] == REVISION
    assert result["baseline"]["created_at"] == "2026-11-02T12:00:00+00:00"
    assert result["counts"]["added"] == 1
    assert result["counts"]["updated"] == 1

    stored_metadata = harness.baselines.get(scope(), "B-2")
    assert stored_metadata == P6Baseline(
        scope(),
        "B-2",
        "Updated Baseline",
        "USER_SELECTED",
        REVISION,
        "2026-11-02T12:00:00+00:00",
    )
    stored = {row.activity_id: row for row in harness.activities.list(scope(), "B-2")}
    assert set(stored) == {"A", "B", "C", "D"}
    assert stored["A"].planned_finish == date(2026, 11, 10)
    assert stored["A"].budgeted_cost == Decimal("1250")
    # Excluded fields keep the stored baseline value.
    assert stored["A"].planned_start == date(2026, 11, 2)
    assert stored["A"].wbs_id == "W-1"
    assert stored["B"].budgeted_cost == Decimal("200")
    assert stored["C"].budgeted_cost == Decimal("300")
    # The source baseline is never mutated.
    assert [(row.activity_id, row.budgeted_cost) for row in harness.activities.list(scope(), "B-1")] == [
        ("A", Decimal("1000")),
        ("B", Decimal("200")),
        ("D", Decimal("400")),
    ]


def test_apply_is_idempotent_for_an_identical_replay_and_rejects_a_conflict(harness):
    first = harness.api.apply(
        scope(),
        "B-1",
        "B-2",
        P6BaselineUpdateSelection(),
        target_name="Updated Baseline",
        expected_revision=REVISION,
        auth_context=auth(),
    )
    replay = harness.api.apply(
        scope(),
        "B-1",
        "B-2",
        P6BaselineUpdateSelection(),
        target_name="Updated Baseline",
        expected_revision=REVISION,
        auth_context=auth(),
    )
    assert replay == first

    with pytest.raises(
        ValueError, match="BASELINE_UPDATE_TARGET_ALREADY_EXISTS"
    ):
        harness.api.apply(
            scope(),
            "B-1",
            "B-2",
            P6BaselineUpdateSelection(),
            target_name="Different Name",
            expected_revision=REVISION,
            auth_context=auth(),
        )


def test_apply_rolls_back_the_target_metadata_when_the_write_fails(harness):
    harness.seed(
        (baseline_row("ONLY", baseline_id="B-9"),),
        (current_value("REPLACEMENT"),),
        baseline_id="B-9",
    )
    with pytest.raises(ValueError, match="BASELINE_ACTIVITIES_EMPTY"):
        harness.api.apply(
            scope(),
            "B-9",
            "B-10",
            P6BaselineUpdateSelection(
                activity_ids=frozenset({"ONLY"}),
                remove_missing_activities=True,
                add_new_activities=False,
            ),
            target_name="Empty Target",
            expected_revision=REVISION,
            auth_context=auth(),
        )
    assert harness.baselines.get(scope(), "B-10") is None
    assert harness.activities.list(scope(), "B-10") == ()


def test_preview_and_apply_fail_closed_on_invalid_boundary_input(harness):
    with pytest.raises(ValueError, match="BASELINE_UPDATE_CONTRACT_VERSION_UNSUPPORTED"):
        harness.api.preview(
            scope(),
            "B-1",
            "B-2",
            P6BaselineUpdateSelection(),
            expected_revision=REVISION,
            auth_context=auth(),
            contract_version="p6-baseline-update-api.v2",
        )
    with pytest.raises(ValueError, match="BASELINE_UPDATE_STALE_REVISION"):
        harness.api.preview(
            scope(),
            "B-1",
            "B-2",
            P6BaselineUpdateSelection(),
            expected_revision=REVISION - 1,
            auth_context=auth(),
        )
    with pytest.raises(ValueError, match="BASELINE_UPDATE_REVISION_INVALID"):
        harness.api.preview(
            scope(),
            "B-1",
            "B-2",
            P6BaselineUpdateSelection(),
            expected_revision=True,  # type: ignore[arg-type]
            auth_context=auth(),
        )
    with pytest.raises(ValueError, match="BASELINE_UPDATE_TARGET_MUST_DIFFER"):
        harness.api.preview(
            scope(),
            "B-1",
            "B-1",
            P6BaselineUpdateSelection(),
            expected_revision=REVISION,
            auth_context=auth(),
        )
    with pytest.raises(ValueError, match="BASELINE_UPDATE_FIELD_UNSUPPORTED"):
        harness.api.preview(
            scope(),
            "B-1",
            "B-2",
            P6BaselineUpdateSelection(fields=frozenset({"actual_cost"})),
            expected_revision=REVISION,
            auth_context=auth(),
        )
    with pytest.raises(ValueError, match="BASELINE_UPDATE_SOURCE_NOT_FOUND"):
        harness.api.preview(
            scope(),
            "MISSING",
            "B-2",
            P6BaselineUpdateSelection(),
            expected_revision=REVISION,
            auth_context=auth(),
        )


def test_authorization_rejects_cross_scope_and_missing_write_permission(harness):
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        harness.api.preview(
            scope(),
            "B-1",
            "B-2",
            P6BaselineUpdateSelection(),
            expected_revision=REVISION,
            auth_context=auth(project_id="project-b"),
        )
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        harness.api.preview(
            scope(),
            "B-1",
            "B-2",
            P6BaselineUpdateSelection(),
            expected_revision=REVISION,
            auth_context=auth(tenant_id="tenant-b"),
        )
    # A read-only role may preview and compare but never apply.
    harness.api.preview(
        scope(),
        "B-1",
        "B-2",
        P6BaselineUpdateSelection(),
        expected_revision=REVISION,
        auth_context=auth(role="viewer"),
    )
    with pytest.raises(AuthorizationError, match="authorization denied"):
        harness.api.apply(
            scope(),
            "B-1",
            "B-2",
            P6BaselineUpdateSelection(),
            target_name="Updated Baseline",
            expected_revision=REVISION,
            auth_context=auth(role="viewer"),
        )


def test_compare_reports_signed_variances_and_one_sided_rows(harness):
    result = harness.api.compare(
        scope(),
        "B-1",
        expected_revision=REVISION,
        auth_context=auth(),
    )

    assert result["kind"] == "p6_baseline_compare"
    assert result["variance_convention"] == BASELINE_VARIANCE_CONVENTION
    assert result["counts"] == {
        "added": 1,
        "changed": 1,
        "deleted": 1,
        "unchanged": 1,
        "total": 4,
    }
    rows = {row["activity_id"]: row for row in result["rows"]}

    changed = rows["A"]
    assert changed["status"] == "CHANGED"
    assert changed["start_variance_days"] == 2
    assert changed["finish_variance_days"] == 4
    assert changed["budget_variance"] == "250"
    assert changed["wbs_changed"] is True
    assert changed["technique_changed"] is True
    assert changed["currency_changed"] is False
    assert changed["baseline"] == {
        "planned_start": "2026-11-02",
        "planned_finish": "2026-11-06",
        "budgeted_cost": "1000",
        "currency": "USD",
        "wbs_id": "W-1",
        "earned_value_technique": EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
    }
    assert changed["current"]["planned_finish"] == "2026-11-10"
    assert changed["current"]["budgeted_cost"] == "1250"

    assert rows["B"]["status"] == "UNCHANGED"
    assert rows["B"]["budget_variance"] == "0"
    assert rows["C"]["status"] == "ADDED"
    assert rows["C"]["start_variance_days"] is None
    assert rows["C"]["baseline"]["planned_start"] is None
    assert rows["C"]["current"]["budgeted_cost"] == "300"
    assert rows["D"]["status"] == "DELETED"
    assert rows["D"]["current"]["planned_start"] is None
    assert rows["D"]["budget_variance"] is None


def test_compare_filters_by_activity_ids(harness):
    result = harness.api.compare(
        scope(),
        "B-1",
        expected_revision=REVISION,
        auth_context=auth(),
        activity_ids=("A",),
    )
    assert [row["activity_id"] for row in result["rows"]] == ["A"]
    assert result["counts"]["total"] == 1
    with pytest.raises(ValueError, match="BASELINE_UPDATE_ACTIVITY_IDS_INVALID"):
        harness.api.compare(
            scope(),
            "B-1",
            expected_revision=REVISION,
            auth_context=auth(),
            activity_ids=(),
        )


def test_sqlite_current_values_are_scoped_and_revision_aware(connection):
    service = P6CurrentActivityApplicationService(
        SQLiteP6CurrentActivityRepository(connection),
        SQLiteTransactionManager(connection),
    )
    service.save_many((current_value("A"), current_value("B", budget="250")))
    stored = service.list_as_baseline(scope())
    assert [row.activity_id for row in stored] == ["A", "B"]
    assert all(row.baseline_id == "CURRENT" for row in stored)
    assert stored[1].budgeted_cost == Decimal("250")

    with pytest.raises(P6CurrentActivityPersistenceError, match="REVISION_CONFLICT"):
        service.list(BackendScope(TENANT, PROJECT, 8))

    # Other tenants and projects never see these rows.
    other_tenant = BackendScope("tenant-b", PROJECT, REVISION)
    other_project = BackendScope(TENANT, "project-b", REVISION)
    assert service.list(other_tenant) == ()
    assert service.list(other_project) == ()

    with pytest.raises(P6CurrentActivityPersistenceError, match="DUPLICATE_CURRENT_ACTIVITY"):
        service.save_many((current_value("A"), current_value("A")))
    with pytest.raises(P6CurrentActivityPersistenceError, match="CURRENT_ACTIVITY_VALUES_EMPTY"):
        service.save_many(())


def test_sqlite_current_values_advance_with_the_project_revision(connection):
    repository = SQLiteP6CurrentActivityRepository(connection)
    service = P6CurrentActivityApplicationService(
        repository, SQLiteTransactionManager(connection)
    )
    service.save_many((current_value("A", budget="100"),))
    service.save_many(
        (current_value("A", s=scope(8), budget="175"),)
    )
    stored = service.list(scope(8))
    assert [(row.activity_id, row.budgeted_cost) for row in stored] == [
        ("A", Decimal("175"))
    ]


def test_concurrent_identical_applies_converge_on_one_target(tmp_path):
    database = tmp_path / "baseline-update.sqlite3"
    seed_connection = sqlite3.connect(database)
    seed = Harness(seed_connection)
    seed.seed(
        (baseline_row("A"),),
        (current_value("A", budget="1500"),),
    )
    seed_connection.commit()
    seed_connection.close()

    barrier = threading.Barrier(2)
    results: list[object] = []
    errors: list[BaseException] = []

    def run() -> None:
        connection = sqlite3.connect(database, timeout=10, check_same_thread=False)
        try:
            harness = Harness(connection)
            barrier.wait(timeout=10)
            results.append(
                harness.api.apply(
                    scope(),
                    "B-1",
                    "B-2",
                    P6BaselineUpdateSelection(),
                    target_name="Concurrent Baseline",
                    expected_revision=REVISION,
                    auth_context=auth(),
                )
            )
        except BaseException as exc:  # pragma: no cover - diagnostic path
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert not errors, errors
    assert len(results) == 2
    assert results[0] == results[1]

    verify_connection = sqlite3.connect(database)
    verify = Harness(verify_connection)
    rows = verify.activities.list(scope(), "B-2")
    assert [(row.activity_id, row.budgeted_cost) for row in rows] == [
        ("A", Decimal("1500"))
    ]
    verify_connection.close()


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
    connection: sqlite3.Connection,
    *,
    roles: frozenset[str] = frozenset({"planner"}),
    clock: datetime | None = None,
):
    now = clock or datetime(2026, 11, 2, 12, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", roles, now + timedelta(hours=2)
    )
    lifecycle = ProjectLifecycleAPI(
        __import__(
            "construction_pm.application.project_lifecycle",
            fromlist=["ProjectLifecycleService"],
        ).ProjectLifecycleService(
            Sessions(session), Projects(), default_project_policy()
        )
    )
    harness = Harness(connection)
    routes = ProjectLifecycleHttpRoutes(
        lifecycle,
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_baseline_update_api=harness.api,
    )
    return routes, harness


def http_call(routes, method: str, path: str, payload: dict | None = None):
    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    return routes.handle(
        method,
        path,
        cookies={"cp_session": "s1"},
        body=body,
    )


def preview_payload(**overrides) -> dict:
    payload = {
        "contract_version": P6_BASELINE_UPDATE_API_VERSION,
        "expected_revision": REVISION,
        "target_baseline_id": "B-2",
        "selection": {"fields": list(BASELINE_UPDATE_FIELDS)},
    }
    payload.update(overrides)
    return payload


def test_http_preview_apply_and_compare_use_the_versioned_contract(connection):
    # Reuse the p1 project id and revision that the lifecycle context exposes.
    s = BackendScope("t1", "p1", REVISION)
    harness = Harness(connection)
    harness.seed(
        (baseline_row("A", s=s), baseline_row("B", s=s, budget="200")),
        (current_value("A", s=s, budget="1250"), current_value("B", s=s, budget="200")),
        s=s,
    )
    routes, _ = http_routes(connection)

    status, headers, body = http_call(
        routes,
        "POST",
        "/api/projects/p1/p6/baselines/B-1/update/preview",
        preview_payload(),
    )
    assert status == 200, body
    assert headers["Content-Type"].startswith("application/json")
    preview = json.loads(body)
    assert preview["kind"] == "p6_baseline_update_preview"
    assert preview["scope"] == {
        "tenant_id": "t1",
        "project_id": "p1",
        "project_revision": REVISION,
    }
    assert preview["updated_activity_ids"] == ["A"]
    assert harness.baselines.get(s, "B-2") is None

    apply_body = preview_payload(
        target_name="HTTP Updated Baseline",
        baseline_type="SECONDARY",
    )
    status, _, body = http_call(
        routes,
        "POST",
        "/api/projects/p1/p6/baselines/B-1/update/apply",
        apply_body,
    )
    assert status == 201, body
    applied = json.loads(body)
    assert applied["kind"] == "p6_baseline_update_apply"
    assert applied["baseline"]["baseline_id"] == "B-2"
    assert applied["baseline"]["baseline_type"] == "SECONDARY"
    assert harness.baselines.get(s, "B-2") is not None

    status, _, body = http_call(
        routes,
        "POST",
        "/api/projects/p1/p6/baselines/B-1/compare",
        {
            "contract_version": P6_BASELINE_UPDATE_API_VERSION,
            "expected_revision": REVISION,
        },
    )
    assert status == 200, body
    compared = json.loads(body)
    assert compared["kind"] == "p6_baseline_compare"
    assert compared["variance_convention"] == BASELINE_VARIANCE_CONVENTION
    assert compared["counts"]["changed"] == 1
    row = next(item for item in compared["rows"] if item["activity_id"] == "A")
    assert row["budget_variance"] == "250"
    assert row["finish_variance_days"] == 0


def test_http_rejects_body_supplied_current_state_and_invalid_contract(connection):
    s = BackendScope("t1", "p1", REVISION)
    harness = Harness(connection)
    harness.seed(
        (baseline_row("A", s=s),),
        (current_value("A", s=s, budget="1250"),),
        s=s,
    )
    routes, _ = http_routes(connection)

    status, _, body = http_call(
        routes,
        "POST",
        "/api/projects/p1/p6/baselines/B-1/update/preview",
        preview_payload(current=[{"activity_id": "A", "budgeted_cost": "1"}]),
    )
    assert status == 400
    assert json.loads(body)["code"] == "BASELINE_UPDATE_CURRENT_BODY_FORBIDDEN"

    status, _, body = http_call(
        routes,
        "POST",
        "/api/projects/p1/p6/baselines/B-1/update/preview",
        preview_payload(contract_version="p6-baseline-update-api.v2"),
    )
    assert status == 400
    assert json.loads(body)["code"] == "BASELINE_UPDATE_CONTRACT_VERSION_UNSUPPORTED"

    status, _, body = http_call(
        routes,
        "POST",
        "/api/projects/p1/p6/baselines/B-1/update/preview",
        preview_payload(unexpected="value"),
    )
    assert status == 400
    assert json.loads(body)["code"] == "P6_BASELINE_UPDATE_REQUEST_INVALID"

    status, _, body = http_call(
        routes,
        "POST",
        "/api/projects/p1/p6/baselines/B-1/update/apply",
        preview_payload(selection=[]),
    )
    assert status == 400
    assert json.loads(body)["code"] == "BASELINE_UPDATE_SELECTION_INVALID"

    status, _, body = http_call(
        routes,
        "POST",
        "/api/projects/p1/p6/baselines/B-1/update/apply",
        preview_payload(target_name=""),
    )
    assert status == 400
    assert json.loads(body)["code"] == "BASELINE_UPDATE_TARGET_NAME_INVALID"


def test_http_maps_stale_revision_missing_baseline_and_permission_errors(connection):
    s = BackendScope("t1", "p1", REVISION)
    harness = Harness(connection)
    harness.seed(
        (baseline_row("A", s=s),),
        (current_value("A", s=s, budget="1250"),),
        s=s,
    )
    routes, _ = http_routes(connection)

    status, _, body = http_call(
        routes,
        "POST",
        "/api/projects/p1/p6/baselines/B-1/update/preview",
        preview_payload(expected_revision=REVISION - 1),
    )
    assert status == 409
    assert json.loads(body)["code"] == "BASELINE_UPDATE_STALE_REVISION"

    status, _, body = http_call(
        routes,
        "POST",
        "/api/projects/p1/p6/baselines/MISSING/update/preview",
        preview_payload(),
    )
    assert status == 404
    assert json.loads(body)["code"] == "BASELINE_UPDATE_SOURCE_NOT_FOUND"

    viewer_routes, _ = http_routes(connection, roles=frozenset({"viewer"}))
    status, _, body = http_call(
        viewer_routes,
        "POST",
        "/api/projects/p1/p6/baselines/B-1/update/apply",
        preview_payload(target_name="Denied"),
    )
    assert status == 403
    assert json.loads(body)["code"] == "AUTHORIZATION_PERMISSION_DENIED"

    status, _, _ = http_call(
        viewer_routes,
        "POST",
        "/api/projects/p1/p6/baselines/B-1/update/preview",
        preview_payload(),
    )
    assert status == 200


def test_http_route_is_absent_without_the_update_api(connection):
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
    routes = ProjectLifecycleHttpRoutes(
        lifecycle, clock=type("Clock", (), {"now": lambda self: now})()
    )
    status, _, body = http_call(
        routes,
        "POST",
        "/api/projects/p1/p6/baselines/B-1/update/preview",
        preview_payload(),
    )
    assert status == 404
    assert json.loads(body)["code"] == "ROUTE_NOT_FOUND"


def test_http_rejects_a_malformed_baseline_path(connection):
    routes, _ = http_routes(connection)
    status, _, body = http_call(
        routes,
        "POST",
        "/api/projects/p1/p6/baselines/B-1/extra/update/preview",
        preview_payload(),
    )
    assert status == 400
    assert json.loads(body)["code"] == "P6_BASELINE_UPDATE_REQUEST_INVALID"


def test_contract_schema_matches_the_versioned_payloads(harness):
    schema_path = (
        Path(__file__).parents[1]
        / "shared/contracts/p6-baseline-update-api.v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert (
        schema["properties"]["contract_version"]["const"]
        == P6_BASELINE_UPDATE_API_VERSION
    )
    variants = {
        variant["properties"]["kind"]["const"]: variant
        for variant in schema["oneOf"]
    }
    assert variants["p6_baseline_compare"]["properties"][
        "variance_convention"
    ]["const"] == BASELINE_VARIANCE_CONVENTION

    payloads = (
        harness.api.preview(
            scope(),
            "B-1",
            "B-2",
            P6BaselineUpdateSelection(),
            expected_revision=REVISION,
            auth_context=auth(),
        ),
        harness.api.apply(
            scope(),
            "B-1",
            "B-2",
            P6BaselineUpdateSelection(),
            target_name="Schema Baseline",
            expected_revision=REVISION,
            auth_context=auth(),
        ),
        harness.api.compare(
            scope(),
            "B-1",
            expected_revision=REVISION,
            auth_context=auth(),
        ),
    )
    root_keys = set(schema["properties"])
    for payload in payloads:
        variant = variants[payload["kind"]]
        assert set(variant["required"]) <= set(payload)
        assert set(payload) <= root_keys | set(variant["properties"])
        assert payload["contract_version"] == P6_BASELINE_UPDATE_API_VERSION
