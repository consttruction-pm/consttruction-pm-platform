from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from construction_pm.activity_master_repository import (
    ActivityMaster,
    SQLiteActivityMasterRepository,
)
from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_activity_period_actual_repository import (
    P6ActivityPeriodActual,
    SQLiteP6ActivityPeriodActualRepository,
)
from construction_pm.p6_baseline_activity_repository import (
    P6BaselineActivity,
    SQLiteP6BaselineActivityRepository,
)
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    SQLiteP6BaselineRepository,
)
from construction_pm.p6_earned_value_read_model import (
    P6_EARNED_VALUE_READ_MODEL_VERSION,
    P6EarnedValueReadModelService,
)
from construction_pm.p6_earned_value_read_model_api import P6EarnedValueReadModelAPI
from construction_pm.p6_expense_repository import P6Expense, SQLiteP6ExpenseRepository
from construction_pm.scheduling.activity import ActivityStatus
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.evm_source import EVM_TECHNIQUE_ZERO_HUNDRED
from construction_pm.scheduling.time_duration import DurationUnit
from construction_pm.wbs_master_repository import (
    SQLiteWBSMasterRepository,
    WBSMaster,
    WBSParentKind,
)

NOW = datetime(2026, 11, 3, tzinfo=timezone.utc)
PROJECT = "p1"
REVISION = 2


class Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def __init__(self) -> None:
        self.item = ProjectSummary(PROJECT, "t1", "EVM Project", REVISION)

    def list_for_user(self, tenant_id: str, user_id: str):
        return (ProjectSummary(PROJECT, tenant_id, self.item.name, REVISION),)

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        if project_id != PROJECT:
            return None
        return ProjectSummary(PROJECT, tenant_id, self.item.name, REVISION)


def _resolver() -> WorkingTimeResolver:
    return WorkingTimeResolver(
        WorkingCalendar(
            working_weekdays=frozenset({0, 1, 2, 3, 4}),
            holidays=frozenset(),
        )
    )


class Harness:
    def __init__(self, roles=frozenset({"project_admin"})) -> None:
        session = AuthenticatedSession(
            "s1", "u1", "t1", roles, NOW + timedelta(hours=1)
        )
        service = ProjectLifecycleService(
            Sessions(session), Projects(), default_project_policy()
        )
        self.lifecycle = ProjectLifecycleAPI(service)
        self.connection = sqlite3.connect(":memory:")
        self.baselines = SQLiteP6BaselineRepository(self.connection)
        self.baseline_activities = SQLiteP6BaselineActivityRepository(self.connection)
        self.activities = SQLiteActivityMasterRepository(self.connection)
        self.actuals = SQLiteP6ActivityPeriodActualRepository(self.connection)
        self.expenses = SQLiteP6ExpenseRepository(self.connection)
        self.wbs = SQLiteWBSMasterRepository(self.connection)
        self.resolver_scopes: list[BackendScope] = []
        policy = default_project_policy()
        self.routes = ProjectLifecycleHttpRoutes(
            self.lifecycle,
            clock=type("Clock", (), {"now": lambda self: NOW})(),
            p6_earned_value_read_api=P6EarnedValueReadModelAPI(
                P6EarnedValueReadModelService(
                    baseline_activities=self.baseline_activities,
                    activities=self.activities,
                    actuals=self.actuals,
                    expenses=self.expenses,
                    resolver_provider=self._resolver_for,
                    wbs_repository=self.wbs,
                ),
                policy,
            ),
        )

    def _resolver_for(self, scope: BackendScope) -> WorkingTimeResolver:
        self.resolver_scopes.append(scope)
        return _resolver()

    def seed(self) -> None:
        scope = BackendScope("t1", PROJECT, REVISION)
        self.baselines.upsert(
            P6Baseline(
                scope, "B-1", "Approved Baseline", "PRIMARY", REVISION,
                "2026-11-01T10:00:00Z", None,
            )
        )
        self.baseline_activities.save_many(
            (
                P6BaselineActivity(
                    scope, "B-1", "A", date(2026, 11, 2), date(2026, 11, 6),
                    Decimal("1000"), "USD", "W-1",
                    "ACTIVITY_PERCENT_COMPLETE",
                ),
                P6BaselineActivity(
                    scope, "B-1", "B", date(2026, 11, 9), date(2026, 11, 13),
                    Decimal("500"), "USD", "W-2",
                    "ZERO_HUNDRED",
                ),
            )
        )
        self.wbs.save(
            WBSMaster(
                scope, "W-ROOT", WBSParentKind.PROJECT, None, "1", "Root", 0
            )
        )
        for wbs_id, code, name in (("W-1", "1.1", "Civil"), ("W-2", "1.2", "Process")):
            self.wbs.save(
                WBSMaster(
                    scope, wbs_id, WBSParentKind.WBS, "W-ROOT", code, name, 0
                )
            )
        self.activities.save(
            ActivityMaster(
                scope=scope,
                activity_id="A",
                duration_value=Decimal("5"),
                duration_unit=DurationUnit.WORKING_DAY,
                actual_start=date(2026, 11, 2),
                percent_complete=50.0,
                status=ActivityStatus.IN_PROGRESS,
                wbs_id="W-1",
            )
        )
        self.activities.save(
            ActivityMaster(
                scope=scope,
                activity_id="B",
                duration_value=Decimal("5"),
                duration_unit=DurationUnit.WORKING_DAY,
                actual_start=date(2026, 11, 9),
                actual_finish=date(2026, 11, 13),
                percent_complete=100.0,
                status=ActivityStatus.COMPLETED,
                wbs_id="W-2",
            )
        )
        self.actuals.upsert(
            P6ActivityPeriodActual(
                scope, "PA", "A", "P1", actual_cost=Decimal("300"), currency="USD"
            )
        )
        self.actuals.upsert(
            P6ActivityPeriodActual(
                scope, "PB", "B", "P1", actual_cost=Decimal("500"), currency="USD"
            )
        )
        self.expenses.upsert(
            P6Expense(
                scope, "E-A", "Activity expense", "cost", activity_id="A",
                actual_cost=Decimal("50"), remaining_cost=Decimal("400"),
                currency="USD",
            )
        )

    def request(self, payload: dict, project_id: str = PROJECT):
        return self.routes.handle(
            "POST",
            f"/api/projects/{project_id}/p6/earned-value",
            cookies={"cp_session": "s1"},
            body=json.dumps(payload).encode(),
        )


def _payload(**overrides) -> dict:
    payload = {
        "baseline_id": "B-1",
        "data_date": "2026-11-04",
        "currency": "USD",
    }
    payload.update(overrides)
    return payload


def test_earned_value_route_returns_the_shared_core_measurement():
    harness = Harness()
    harness.seed()
    status, _, raw = harness.request(_payload())
    assert status == 200
    body = json.loads(raw)
    assert body["contract_version"] == P6_EARNED_VALUE_READ_MODEL_VERSION
    assert body["kind"] == "p6_earned_value_read_model"
    assert body["baseline_id"] == "B-1"
    assert body["data_date"] == "2026-11-04"
    assert body["scope"] == {
        "tenant_id": "t1",
        "project_id": PROJECT,
        "project_revision": REVISION,
    }
    assert Decimal(body["earned_value"]["planned_value"]) == Decimal("600.00")
    assert Decimal(body["earned_value"]["earned_value"]) == Decimal("1000.00")
    assert Decimal(body["earned_value"]["actual_cost"]) == Decimal("850")
    assert Decimal(body["earned_value"]["budget_at_completion"]) == Decimal("1500")
    assert Decimal(body["earned_value"]["estimate_to_complete"]) == Decimal("400")
    assert [row["activity_id"] for row in body["activities"]] == ["A", "B"]
    assert [row["wbs_id"] for row in body["wbs_rollups"]] == ["W-1", "W-2"]
    assert harness.resolver_scopes == [BackendScope("t1", PROJECT, REVISION)]


def test_earned_value_route_applies_explicit_wbs_settings():
    harness = Harness()
    harness.seed()
    status, _, raw = harness.request(
        _payload(
            settings={
                "technique_overrides": [
                    {"wbs_id": "W-ROOT", "technique": EVM_TECHNIQUE_ZERO_HUNDRED}
                ]
            }
        )
    )
    assert status == 200
    body = json.loads(raw)
    assert Decimal(body["earned_value"]["earned_value"]) == Decimal("500.00")
    assert body["activities"][0]["earned_value_technique"] == (
        EVM_TECHNIQUE_ZERO_HUNDRED
    )


def test_earned_value_route_rejects_invalid_selections_and_contracts():
    harness = Harness()
    harness.seed()

    status, _, raw = harness.request(_payload(unknown=True))
    assert status == 400
    assert json.loads(raw)["code"] == "EVM_REQUEST_UNKNOWN_FIELD"

    status, _, raw = harness.request(_payload(data_date="not-a-date"))
    assert status == 400
    assert json.loads(raw)["code"] == "EVM_DATA_DATE_INVALID"

    status, _, raw = harness.request(_payload(baseline_id="missing"))
    assert status == 404
    assert json.loads(raw)["code"] == "EVM_BASELINE_ACTIVITIES_EMPTY:missing"

    status, _, raw = harness.request(
        _payload(contract_version="p6-earned-value-read-model.v2")
    )
    assert status == 400
    assert json.loads(raw)["code"] == "EVM_CONTRACT_VERSION_UNSUPPORTED"

    status, _, raw = harness.request(_payload(performance_factor=True))
    assert status == 400
    assert json.loads(raw)["code"] == "EVM_PERFORMANCE_FACTOR_INVALID"

    status, _, raw = harness.request(
        _payload(settings={"technique_overrides": "W-ROOT"})
    )
    assert status == 400
    assert json.loads(raw)["code"] == "EVM_TECHNIQUE_OVERRIDE_INVALID"

    status, _, raw = harness.request(_payload(etc_method="UNKNOWN_METHOD"))
    assert status == 400
    assert json.loads(raw)["code"] == "EARNED_VALUE_ETC_METHOD_UNSUPPORTED"


def test_earned_value_route_maps_currency_conflicts_and_authorization():
    harness = Harness()
    harness.seed()
    scope = BackendScope("t1", PROJECT, REVISION)
    harness.actuals.upsert(
        P6ActivityPeriodActual(
            scope, "PA-EUR", "A", "P2", actual_cost=Decimal("10"), currency="EUR"
        )
    )
    status, _, raw = harness.request(_payload())
    assert status == 409
    assert json.loads(raw)["code"] == "EVM_ACTUAL_CURRENCY_MISMATCH:A"

    viewer = Harness(roles=frozenset({"viewer"}))
    viewer.seed()
    status, _, _ = viewer.request(_payload())
    assert status == 200

    status, _, raw = harness.request(_payload(), project_id="unknown")
    assert status == 403
    assert json.loads(raw)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"


def test_earned_value_payload_matches_the_versioned_contract_schema():
    schema = json.loads(
        (
            Path(__file__).parents[1]
            / "shared/contracts/p6-earned-value-read-model.v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert schema["properties"]["contract_version"]["const"] == (
        P6_EARNED_VALUE_READ_MODEL_VERSION
    )
    assert schema["properties"]["kind"]["const"] == "p6_earned_value_read_model"

    harness = Harness()
    harness.seed()
    status, _, raw = harness.request(_payload())
    assert status == 200
    body = json.loads(raw)
    assert set(body) == set(schema["required"])
    assert set(body) <= set(schema["properties"])

    activity_schema = schema["$defs"]["activity"]
    activity = body["activities"][0]
    assert set(activity) == set(activity_schema["required"])
    assert set(activity) <= set(activity_schema["properties"])

    rollup_schema = schema["$defs"]["wbsRollup"]
    assert set(body["wbs_rollups"][0]) == set(rollup_schema["required"])

    earned = schema["properties"]["earned_value"]
    assert set(body["earned_value"]) == set(earned["required"])
    assert set(body["earned_value"]) <= set(earned["properties"])
