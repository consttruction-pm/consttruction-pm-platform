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
from construction_pm.cost_api import COST_API_VERSION, CostAPI
from construction_pm.cost_application import CostApplicationService
from construction_pm.cost_persistence import CostAccount, Expense, SQLiteCostStore

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)


def context(role: str = "planner", *, user: str = "u-1") -> AuthorizationContext:
    return AuthorizationContext("T-1", "P-1", user, frozenset({role}))


def account(**changes: object) -> CostAccount:
    values = {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "account_id": "CA-1",
        "name": "Direct costs",
        "parent_account_id": None,
        "description": "Direct project costs",
        "is_default": False,
    }
    values.update(changes)
    return CostAccount(**values)


def expense(**changes: object) -> Expense:
    values = {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "expense_id": "EX-1",
        "name": "Concrete delivery",
        "category": "material",
        "currency": "USD",
        "activity_id": "A-1000",
        "wbs_id": "WBS-1",
        "cost_account_id": "CA-1",
        "expense_date": "2026-11-01",
        "accrual_date": "2026-11-02",
        "planned_amount": Decimal("1000.00"),
        "actual_amount": Decimal("900.00"),
        "remaining_amount": Decimal("100.00"),
        "note": "Batch 4",
    }
    values.update(changes)
    return Expense(**values)


@pytest.fixture()
def api() -> CostAPI:
    connection = sqlite3.connect(":memory:")
    store = SQLiteCostStore(connection)
    store.initialize()
    return CostAPI(
        CostApplicationService(
            store, default_project_policy(), SQLiteTransactionManager(connection)
        )
    )


def test_empty_reads_carry_the_contract_version(api) -> None:
    assert api.list_accounts(
        tenant_id="T-1", project_id="P-1", context=context()
    ) == {"contract_version": COST_API_VERSION, "cost_accounts": []}
    assert api.list_expenses(
        tenant_id="T-1", project_id="P-1", context=context()
    ) == {"contract_version": COST_API_VERSION, "expenses": []}
    assert api.summary(
        tenant_id="T-1", project_id="P-1", context=context()
    ) == {"contract_version": COST_API_VERSION, "currencies": []}


def test_account_lifecycle_serialises_default_copy_and_history(api) -> None:
    created = api.create_account(
        account(),
        idempotency_key="k-1",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert created == {
        "contract_version": COST_API_VERSION,
        "account_id": "CA-1",
        "name": "Direct costs",
        "parent_account_id": None,
        "description": "Direct project costs",
        "is_default": False,
        "revision": 1,
    }
    updated = api.update_account(
        account(name="Direct project costs"),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert updated["revision"] == 2
    assert api.update_account(
        account(name="Stale"),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )["code"] == "COST_REVISION_CONFLICT"

    defaulted = api.set_default_account(
        tenant_id="T-1",
        project_id="P-1",
        account_id="CA-1",
        expected_revision=2,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert defaulted["cost_accounts"][0]["is_default"] is True
    assert defaulted["cost_accounts"][0]["revision"] == 3

    copied = api.copy_account(
        tenant_id="T-1",
        project_id="P-1",
        source_account_id="CA-1",
        account_id="CA-2",
        name="Direct costs copy",
        idempotency_key="k-2",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert copied["parent_account_id"] is None
    assert copied["description"] == "Direct project costs"
    assert copied["is_default"] is False

    history = api.account_history(
        tenant_id="T-1", project_id="P-1", account_id="CA-1", context=context()
    )
    assert [event["event_type"] for event in history["events"]] == [
        "created",
        "updated",
        "default_changed",
    ]
    assert history["events"][0]["occurred_at"] == NOW.isoformat()

    deleted = api.delete_account(
        tenant_id="T-1",
        project_id="P-1",
        account_id="CA-2",
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert deleted == {
        "contract_version": COST_API_VERSION,
        "account_id": "CA-2",
        "deleted": True,
    }


def test_expense_lifecycle_serialises_money_filters_and_summary(api) -> None:
    api.create_account(
        account(), idempotency_key="k-1", context=context(), actor_id="u-1", occurred_at=NOW
    )
    created = api.create_expense(
        expense(),
        idempotency_key="e-1",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert created == {
        "contract_version": COST_API_VERSION,
        "expense_id": "EX-1",
        "name": "Concrete delivery",
        "category": "material",
        "currency": "USD",
        "activity_id": "A-1000",
        "wbs_id": "WBS-1",
        "cost_account_id": "CA-1",
        "expense_date": "2026-11-01",
        "accrual_date": "2026-11-02",
        "planned_amount": "1000.00",
        "actual_amount": "900.00",
        "remaining_amount": "100.00",
        "note": "Batch 4",
        "revision": 1,
    }
    updated = api.update_expense(
        expense(actual_amount=Decimal("1000.00")),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert updated["actual_amount"] == "1000.00" and updated["revision"] == 2
    stale = api.update_expense(
        expense(actual_amount=Decimal("1.00")),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert stale["code"] == "COST_REVISION_CONFLICT"

    filtered = api.list_expenses(
        tenant_id="T-1",
        project_id="P-1",
        context=context(),
        category="material",
        cost_account_id="CA-1",
        activity_id="A-1000",
        search="concrete",
    )
    assert [item["expense_id"] for item in filtered["expenses"]] == ["EX-1"]

    summary = api.summary(tenant_id="T-1", project_id="P-1", context=context())
    assert summary["currencies"] == [
        {
            "currency": "USD",
            "planned_amount": "1000.00",
            "actual_amount": "1000.00",
            "remaining_amount": "100.00",
            "expense_count": 1,
        }
    ]
    history = api.expense_history(
        tenant_id="T-1", project_id="P-1", expense_id="EX-1", context=context()
    )
    assert [event["event_type"] for event in history["events"]] == ["created", "updated"]


def test_error_envelopes_cover_missing_conflict_and_authorization(api) -> None:
    missing = api.read_expense(
        tenant_id="T-1", project_id="P-1", expense_id="EX-404", context=context()
    )
    assert missing == {
        "contract_version": COST_API_VERSION,
        "category": "validation",
        "code": "EXPENSE_NOT_FOUND",
        "message": "EXPENSE_NOT_FOUND",
        "retryable": False,
    }
    denied = api.list_accounts(
        tenant_id="T-1",
        project_id="P-1",
        context=AuthorizationContext("T-1", "P-1", "x", frozenset()),
    )
    assert denied["category"] == "authorization"
    assert denied["code"] == "COST_PERMISSION_DENIED"
    duplicate = api.create_account(
        account(),
        idempotency_key="k-1",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert "revision" in duplicate
    conflict = api.create_account(
        account(),
        idempotency_key="k-2",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert conflict["code"] == "COST_ACCOUNT_ALREADY_EXISTS"
    assert conflict["category"] == "conflict"
