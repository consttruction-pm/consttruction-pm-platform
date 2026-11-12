from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from construction_pm.application.authorization import (
    AuthorizationContext,
    default_project_policy,
)
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.risk_api import RISK_API_VERSION, RiskAPI
from construction_pm.risk_application import RiskApplicationService
from construction_pm.risk_persistence import SQLiteRiskStore, Risk

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)


def context(role: str = "planner", user: str = "u-1") -> AuthorizationContext:
    return AuthorizationContext("T-1", "P-1", user, frozenset({role}))


def risk(**changes: object) -> Risk:
    values = {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "risk_id": "RK-1",
        "title": "Supplier lead time slips",
        "description": "Primary steel supplier may miss the framed date.",
        "category": "schedule",
        "status": "open",
        "probability": 3,
        "impact": 4,
        "response_strategy": "mitigate",
        "owner": "u-owner",
        "date_identified": "2026-11-01",
        "response_owner": "u-response",
        "response_due_date": "2026-12-01",
        "responsible_manager": "u-manager",
    }
    values.update(changes)
    return Risk(**values)


def build_api() -> RiskAPI:
    connection = sqlite3.connect(":memory:")
    store = SQLiteRiskStore(connection)
    store.initialize()
    return RiskAPI(
        RiskApplicationService(
            store, default_project_policy(), SQLiteTransactionManager(connection)
        )
    )


def test_flat_versioned_dto_exposes_derived_exposure() -> None:
    api = build_api()
    created = api.create_risk(
        risk(),
        idempotency_key="k-1",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert created["contract_version"] == RISK_API_VERSION
    assert created["risk_id"] == "RK-1"
    assert created["probability"] == 3 and created["impact"] == 4
    assert created["score"] == 12
    assert created["exposure_level"] == "high"
    assert created["revision"] == 1
    assert created["response_owner"] == "u-response"
    assert created["closure_note"] is None

    listed = api.list_risks(
        tenant_id="T-1", project_id="P-1", context=context("viewer", user="v-1")
    )
    assert [item["risk_id"] for item in listed["risks"]] == ["RK-1"]

    read = api.read_risk(
        tenant_id="T-1", project_id="P-1", risk_id="RK-1", context=context()
    )
    assert read["title"] == "Supplier lead time slips"


def test_update_status_and_history_round_trip() -> None:
    api = build_api()
    api.create_risk(
        risk(), idempotency_key="k-1", context=context(), actor_id="u-1", occurred_at=NOW
    )
    updated = api.update_risk(
        risk(status="mitigating"),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
        reason="Plan approved",
    )
    assert updated["status"] == "mitigating" and updated["revision"] == 2
    history = api.risk_history(
        tenant_id="T-1", project_id="P-1", risk_id="RK-1", context=context()
    )
    assert history["contract_version"] == RISK_API_VERSION
    assert [event["event_type"] for event in history["events"]] == [
        "created",
        "status_changed",
    ]
    assert history["events"][1]["reason"] == "Plan approved"

    stale = api.update_risk(
        risk(status="monitoring"),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert stale["code"] == "RISK_REVISION_CONFLICT"
    assert stale["category"] == "conflict" and stale["retryable"] is True


def test_filters_delete_and_errors() -> None:
    api = build_api()
    api.create_risk(
        risk(), idempotency_key="k-1", context=context(), actor_id="u-1", occurred_at=NOW
    )
    api.create_risk(
        risk(
            risk_id="RK-2",
            title="Currency exposure",
            category="commercial",
            probability=5,
            impact=5,
            response_strategy="transfer",
        ),
        idempotency_key="k-2",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    filtered = api.list_risks(
        tenant_id="T-1",
        project_id="P-1",
        context=context(),
        category="commercial",
        exposure="critical",
        search="currency",
    )
    assert [item["risk_id"] for item in filtered["risks"]] == ["RK-2"]

    denied = api.list_risks(
        tenant_id="T-1", project_id="P-1", context=context("viewer", user="v-1"),
    )
    assert denied["risks"][0]["risk_id"] == "RK-2"

    removed = api.delete_risk(
        tenant_id="T-1",
        project_id="P-1",
        risk_id="RK-2",
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert removed["deleted"] is True
    missing = api.read_risk(
        tenant_id="T-1", project_id="P-1", risk_id="RK-2", context=context()
    )
    assert missing["code"] == "RISK_NOT_FOUND" and missing["category"] == "validation"

    viewer = api.create_risk(
        risk(risk_id="RK-3"),
        idempotency_key="k-3",
        context=context("viewer", user="v-1"),
        actor_id="v-1",
        occurred_at=NOW,
    )
    assert viewer["code"] == "RISK_PERMISSION_DENIED"
    assert viewer["category"] == "authorization"
