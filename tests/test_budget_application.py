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
from construction_pm.budget_application import (
    BudgetApplicationService,
    BudgetAuthorizationError,
)
from construction_pm.budget_persistence import (
    BudgetChange,
    BudgetIdempotencyReuse,
    BudgetLine,
    BudgetRevisionConflict,
    FundingSource,
    SQLiteBudgetStore,
)

NOW = datetime(2026, 11, 12, 11, 0, tzinfo=timezone.utc)


def context(role: str = "planner", *, tenant: str = "T-1", project: str = "P-1", user: str = "u-1") -> AuthorizationContext:
    return AuthorizationContext(tenant, project, user, frozenset({role}))


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


def change(**changes: object) -> BudgetChange:
    values = {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "budget_line_id": "BL-1",
        "change_id": "BC-1",
        "amount": Decimal("250.00"),
        "reason": "Extra curing",
    }
    values.update(changes)
    return BudgetChange(**values)


def funding(**changes: object) -> FundingSource:
    values = {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "funding_id": "FS-1",
        "name": "Owner equity",
        "source_type": "internal",
        "currency": "USD",
        "amount": Decimal("400.00"),
    }
    values.update(changes)
    return FundingSource(**values)


@pytest.fixture()
def service() -> BudgetApplicationService:
    connection = sqlite3.connect(":memory:")
    store = SQLiteBudgetStore(connection)
    store.initialize()
    return BudgetApplicationService(
        store, default_project_policy(), SQLiteTransactionManager(connection)
    )


def test_viewer_reads_but_roles_without_read_permission_are_denied(service) -> None:
    service.create_line(
        line(), idempotency_key="k-1", context=context(), actor_id="u-1", occurred_at=NOW
    )
    viewer = context("viewer", user="v-1")
    assert len(service.list_lines(tenant_id="T-1", project_id="P-1", context=viewer)) == 1
    assert service.read_line(
        tenant_id="T-1", project_id="P-1", budget_line_id="BL-1", context=viewer
    ).revision == 1

    anonymous = AuthorizationContext("T-1", "P-1", "x-1", frozenset())
    with pytest.raises(BudgetAuthorizationError, match="BUDGET_PERMISSION_DENIED"):
        service.list_lines(tenant_id="T-1", project_id="P-1", context=anonymous)


def test_cross_scope_and_actor_spoofing_are_rejected(service) -> None:
    with pytest.raises(BudgetAuthorizationError, match="BUDGET_CROSS_SCOPE_ACCESS"):
        service.list_lines(tenant_id="T-2", project_id="P-1", context=context())
    with pytest.raises(BudgetAuthorizationError, match="BUDGET_CROSS_SCOPE_ACCESS"):
        service.create_line(
            line(project_id="P-2"),
            idempotency_key="k-1",
            context=context(),
            actor_id="u-1",
            occurred_at=NOW,
        )
    with pytest.raises(BudgetAuthorizationError, match="BUDGET_ACTOR_MISMATCH"):
        service.create_line(
            line(), idempotency_key="k-1", context=context(), actor_id="u-2", occurred_at=NOW
        )


def test_summary_keeps_original_approved_pending_and_funding_distinct(service) -> None:
    service.create_line(
        line(), idempotency_key="k-1", context=context(), actor_id="u-1", occurred_at=NOW
    )
    service.create_change(
        change(), context=context(), actor_id="u-1", occurred_at=NOW
    )
    service.create_change(
        change(change_id="BC-2", amount=Decimal("100.00"), reason="Second"),
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    service.transition_change(
        tenant_id="T-1",
        project_id="P-1",
        change_id="BC-1",
        status="approved",
        expected_revision=1,
        context=context("project_admin"),
        actor_id="u-1",
        occurred_at=NOW,
    )
    service.create_funding(
        funding(), idempotency_key="f-1", context=context(), actor_id="u-1", occurred_at=NOW
    )
    service.create_funding(
        funding(funding_id="FS-2", currency="EUR", amount=Decimal("50.00")),
        idempotency_key="f-2",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )

    rows = service.summary(
        tenant_id="T-1", project_id="P-1", context=context("viewer", user="v-1")
    )
    assert [(row.currency, row.original_budget, row.approved_changes, row.current_budget, row.pending_changes, row.funding, row.funding_balance) for row in rows] == [
        ("EUR", Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), Decimal("50.00"), Decimal("-50.00")),
        ("USD", Decimal("1000.00"), Decimal("250.00"), Decimal("1250.00"), Decimal("100.00"), Decimal("400.00"), Decimal("850.00")),
    ]


def test_currency_cannot_change_once_changes_exist(service) -> None:
    service.create_line(
        line(), idempotency_key="k-1", context=context(), actor_id="u-1", occurred_at=NOW
    )
    service.update_line(
        line(description="Concrete works, renamed"),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    service.create_change(change(), context=context(), actor_id="u-1", occurred_at=NOW)
    with pytest.raises(ValueError, match="BUDGET_CURRENCY_LOCKED_BY_CHANGES"):
        service.update_line(
            line(currency="EUR"),
            expected_revision=2,
            context=context(),
            actor_id="u-1",
            occurred_at=NOW,
        )
    stale = service.read_line(
        tenant_id="T-1", project_id="P-1", budget_line_id="BL-1", context=context()
    )
    assert stale.revision == 2


def test_changes_must_start_pending_and_only_admin_approves(service) -> None:
    service.create_line(
        line(), idempotency_key="k-1", context=context(), actor_id="u-1", occurred_at=NOW
    )
    with pytest.raises(ValueError, match="BUDGET_CHANGE_MUST_START_PENDING"):
        service.create_change(
            change(status="approved"), context=context(), actor_id="u-1", occurred_at=NOW
        )
    service.create_change(change(), context=context(), actor_id="u-1", occurred_at=NOW)
    with pytest.raises(BudgetAuthorizationError, match="BUDGET_APPROVAL_REQUIRES_ADMIN"):
        service.transition_change(
            tenant_id="T-1",
            project_id="P-1",
            change_id="BC-1",
            status="approved",
            expected_revision=1,
            context=context(),
            actor_id="u-1",
            occurred_at=NOW,
        )


def test_error_dto_maps_each_failure_to_the_expected_category() -> None:
    error = BudgetApplicationService.error_dto(KeyError("BUDGET_LINE_NOT_FOUND"))
    assert error.code == "BUDGET_LINE_NOT_FOUND" and error.category.value == "validation"
    error = BudgetApplicationService.error_dto(BudgetRevisionConflict("BUDGET_REVISION_CONFLICT"))
    assert error.category.value == "conflict" and error.retryable is True
    error = BudgetApplicationService.error_dto(BudgetIdempotencyReuse("BUDGET_IDEMPOTENCY_KEY_REUSE"))
    assert error.category.value == "conflict" and error.retryable is False
    error = BudgetApplicationService.error_dto(BudgetAuthorizationError("BUDGET_PERMISSION_DENIED"))
    assert error.category.value == "authorization"
    error = BudgetApplicationService.error_dto(ValueError("BUDGET_CURRENCY_LOCKED_BY_CHANGES"))
    assert error.category.value == "validation"
