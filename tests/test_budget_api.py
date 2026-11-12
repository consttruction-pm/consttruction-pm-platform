from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    default_project_policy,
)
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.budget_api import BUDGET_API_VERSION, BudgetAPI
from construction_pm.budget_application import BudgetApplicationService
from construction_pm.budget_persistence import (
    BudgetChange,
    BudgetLine,
    FundingSource,
    SQLiteBudgetStore,
)

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)


def context(role: str = "planner", *, user: str = "u-1") -> AuthorizationContext:
    return AuthorizationContext("T-1", "P-1", user, frozenset({role}))


def line(**changes: object) -> BudgetLine:
    values = {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "budget_line_id": "BL-1",
        "description": "Concrete works",
        "currency": "USD",
        "original_amount": Decimal("1000.00"),
        "cost_account_id": "CA-1",
    }
    values.update(changes)
    return BudgetLine(**values)


@pytest.fixture()
def api() -> BudgetAPI:
    connection = sqlite3.connect(":memory:")
    store = SQLiteBudgetStore(connection)
    store.initialize()
    return BudgetAPI(
        BudgetApplicationService(
            store, default_project_policy(), SQLiteTransactionManager(connection)
        )
    )


def test_empty_reads_carry_the_contract_version(api) -> None:
    assert api.list_lines(
        tenant_id="T-1", project_id="P-1", context=context()
    ) == {"contract_version": BUDGET_API_VERSION, "budget_lines": []}
    assert api.list_funding(
        tenant_id="T-1", project_id="P-1", context=context()
    ) == {"contract_version": BUDGET_API_VERSION, "funding_sources": []}
    assert api.summary(
        tenant_id="T-1", project_id="P-1", context=context()
    ) == {"contract_version": BUDGET_API_VERSION, "currencies": []}


def test_line_lifecycle_serialises_money_history_and_summary(api) -> None:
    created = api.create_line(
        line(),
        idempotency_key="k-1",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert created == {
        "contract_version": BUDGET_API_VERSION,
        "budget_line_id": "BL-1",
        "description": "Concrete works",
        "currency": "USD",
        "original_amount": "1000.00",
        "cost_account_id": "CA-1",
        "period_id": None,
        "revision": 1,
    }
    updated = api.update_line(
        line(description="Concrete works revised"),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
        audit_reason="scope",
    )
    assert updated["revision"] == 2
    assert api.update_line(
        line(description="Stale"),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )["code"] == "BUDGET_REVISION_CONFLICT"

    api.create_change(
        BudgetChange("T-1", "P-1", "BL-1", "BC-1", Decimal("-100.00"), "Reduced scope"),
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    changes = api.list_changes(
        tenant_id="T-1", project_id="P-1", budget_line_id="BL-1", context=context()
    )
    assert changes["changes"][0]["amount"] == "-100.00"
    assert changes["changes"][0]["status"] == "pending"
    assert changes["changes"][0]["budget_line_id"] == "BL-1"

    approval = api.transition_change(
        tenant_id="T-1",
        project_id="P-1",
        change_id="BC-1",
        status="approved",
        expected_revision=1,
        context=context("project_admin"),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert approval["status"] == "approved" and approval["revision"] == 2

    history = api.line_history(
        tenant_id="T-1", project_id="P-1", budget_line_id="BL-1", context=context()
    )
    assert [event["event_type"] for event in history["events"]] == ["created", "updated"]
    assert history["events"][0]["occurred_at"] == NOW.isoformat()

    summary = api.summary(tenant_id="T-1", project_id="P-1", context=context())
    assert summary["currencies"] == [
        {
            "currency": "USD",
            "original_budget": "1000.00",
            "approved_changes": "-100.00",
            "current_budget": "900.00",
            "pending_changes": "0.00",
            "funding": "0.00",
            "funding_balance": "900.00",
        }
    ]


def test_funding_api_and_error_envelopes(api) -> None:
    created = api.create_funding(
        FundingSource("T-1", "P-1", "FS-1", "Owner equity", "internal", "USD", Decimal("400.00")),
        idempotency_key="f-1",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert created["amount"] == "400.00" and created["revision"] == 1
    assert api.create_funding(
        FundingSource("T-1", "P-1", "FS-1", "Owner equity", "internal", "USD", Decimal("400.00")),
        idempotency_key="f-1",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    ) == created
    updated = api.update_funding(
        FundingSource("T-1", "P-1", "FS-1", "Owner equity", "internal", "USD", Decimal("1.00")),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert updated["amount"] == "1.00" and updated["revision"] == 2
    stale = api.update_funding(
        FundingSource("T-1", "P-1", "FS-1", "Owner equity", "internal", "USD", Decimal("2.00")),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert stale["code"] == "BUDGET_REVISION_CONFLICT"
    missing = api.read_line(
        tenant_id="T-1", project_id="P-1", budget_line_id="BL-404", context=context()
    )
    assert missing == {
        "contract_version": BUDGET_API_VERSION,
        "category": "validation",
        "code": "BUDGET_LINE_NOT_FOUND",
        "message": "BUDGET_LINE_NOT_FOUND",
        "retryable": False,
    }
    denied = api.list_lines(
        tenant_id="T-1", project_id="P-1", context=AuthorizationContext("T-1", "P-1", "x", frozenset())
    )
    assert denied["category"] == "authorization"
    assert denied["code"] == "BUDGET_PERMISSION_DENIED"
