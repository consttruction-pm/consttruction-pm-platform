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
from construction_pm.cost_application import CostApplicationService, CostAuthorizationError
from construction_pm.cost_persistence import (
    CostAccount,
    CostIdempotencyReuse,
    CostRevisionConflict,
    Expense,
    SQLiteCostStore,
)

NOW = datetime(2026, 11, 12, 11, 0, tzinfo=timezone.utc)


def context(
    role: str = "planner", *, tenant: str = "T-1", project: str = "P-1", user: str = "u-1"
) -> AuthorizationContext:
    return AuthorizationContext(tenant, project, user, frozenset({role}))


def account(**changes: object) -> CostAccount:
    values = {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "account_id": "CA-1",
        "name": "Direct costs",
        "parent_account_id": None,
        "description": None,
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
        "cost_account_id": None,
        "expense_date": "2026-11-01",
        "accrual_date": "2026-11-02",
        "planned_amount": Decimal("1000.00"),
        "actual_amount": Decimal("900.00"),
        "remaining_amount": Decimal("100.00"),
        "note": None,
    }
    values.update(changes)
    return Expense(**values)


@pytest.fixture()
def service() -> CostApplicationService:
    connection = sqlite3.connect(":memory:")
    store = SQLiteCostStore(connection)
    store.initialize()
    return CostApplicationService(
        store, default_project_policy(), SQLiteTransactionManager(connection)
    )


def test_viewer_reads_but_anonymous_and_cross_scope_are_denied(service) -> None:
    service.create_account(
        account(), idempotency_key="k-1", context=context(), actor_id="u-1", occurred_at=NOW
    )
    viewer = context("viewer", user="v-1")
    assert len(service.list_accounts(tenant_id="T-1", project_id="P-1", context=viewer)) == 1
    assert service.read_account(
        tenant_id="T-1", project_id="P-1", account_id="CA-1", context=viewer
    ).revision == 1
    anonymous = AuthorizationContext("T-1", "P-1", "x-1", frozenset())
    with pytest.raises(CostAuthorizationError, match="COST_PERMISSION_DENIED"):
        service.list_accounts(tenant_id="T-1", project_id="P-1", context=anonymous)
    with pytest.raises(CostAuthorizationError, match="COST_CROSS_SCOPE_ACCESS"):
        service.list_expenses(tenant_id="T-2", project_id="P-1", context=context())


def test_actor_spoofing_and_viewer_writes_are_rejected(service) -> None:
    with pytest.raises(CostAuthorizationError, match="COST_ACTOR_MISMATCH"):
        service.create_account(
            account(), idempotency_key="k-1", context=context(), actor_id="u-2", occurred_at=NOW
        )
    viewer = context("viewer", user="u-1")
    with pytest.raises(CostAuthorizationError, match="COST_PERMISSION_DENIED"):
        service.create_expense(
            expense(), idempotency_key="e-1", context=viewer, actor_id="u-1", occurred_at=NOW
        )


def test_account_copy_clones_parent_and_description_without_default(service) -> None:
    service.create_account(
        account(is_default=True, description="Direct project costs"),
        idempotency_key="k-1",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    copied = service.copy_account(
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
    assert copied.account.account_id == "CA-2"
    assert copied.account.description == "Direct project costs"
    assert copied.account.is_default is False
    with pytest.raises(CostIdempotencyReuse, match="COST_IDEMPOTENCY_KEY_REUSE"):
        service.copy_account(
            tenant_id="T-1",
            project_id="P-1",
            source_account_id="CA-1",
            account_id="CA-3",
            name="Different",
            idempotency_key="k-2",
            context=context(),
            actor_id="u-1",
            occurred_at=NOW,
        )


def test_set_default_requires_current_revision(service) -> None:
    service.create_account(
        account(), idempotency_key="k-1", context=context(), actor_id="u-1", occurred_at=NOW
    )
    service.create_account(
        account(account_id="CA-2", name="Concrete"),
        idempotency_key="k-2",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    with pytest.raises(CostRevisionConflict, match="COST_REVISION_CONFLICT"):
        service.set_default_account(
            tenant_id="T-1",
            project_id="P-1",
            account_id="CA-2",
            expected_revision=2,
            context=context(),
            actor_id="u-1",
            occurred_at=NOW,
        )
    rows = service.set_default_account(
        tenant_id="T-1",
        project_id="P-1",
        account_id="CA-2",
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert {row.account.account_id: row.account.is_default for row in rows} == {
        "CA-1": False,
        "CA-2": True,
    }


def test_expense_summary_groups_currencies_and_counts(service) -> None:
    service.create_expense(
        expense(), idempotency_key="e-1", context=context(), actor_id="u-1", occurred_at=NOW
    )
    service.create_expense(
        expense(
            expense_id="EX-2",
            currency="EUR",
            planned_amount=Decimal("250.00"),
            actual_amount=Decimal("200.00"),
            remaining_amount=Decimal("50.00"),
        ),
        idempotency_key="e-2",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    service.create_expense(
        expense(
            expense_id="EX-3",
            planned_amount=Decimal("1.00"),
            actual_amount=None,
            remaining_amount=None,
        ),
        idempotency_key="e-3",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    rows = service.summary(
        tenant_id="T-1", project_id="P-1", context=context("viewer", user="v-1")
    )
    assert [
        (row.currency, row.planned_amount, row.actual_amount, row.remaining_amount, row.expense_count)
        for row in rows
    ] == [
        ("EUR", Decimal("250.00"), Decimal("200.00"), Decimal("50.00"), 1),
        ("USD", Decimal("1001.00"), Decimal("900.00"), Decimal("100.00"), 2),
    ]


def test_error_dto_maps_each_failure_to_the_expected_category() -> None:
    error = CostApplicationService.error_dto(KeyError("EXPENSE_NOT_FOUND"))
    assert error.code == "EXPENSE_NOT_FOUND" and error.category.value == "validation"
    error = CostApplicationService.error_dto(CostRevisionConflict("COST_REVISION_CONFLICT"))
    assert error.category.value == "conflict" and error.retryable is True
    error = CostApplicationService.error_dto(CostIdempotencyReuse("COST_IDEMPOTENCY_KEY_REUSE"))
    assert error.category.value == "conflict" and error.retryable is False
    error = CostApplicationService.error_dto(CostAuthorizationError("COST_PERMISSION_DENIED"))
    assert error.category.value == "authorization"
    error = CostApplicationService.error_dto(ValueError("COST_ACCOUNT_HAS_CHILDREN"))
    assert error.category.value == "conflict"
    error = CostApplicationService.error_dto(ValueError("INVALID_EXPENSE_CATEGORY"))
    assert error.category.value == "validation"
