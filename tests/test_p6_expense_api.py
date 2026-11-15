from decimal import Decimal

import pytest

from construction_pm.application.authorization import (
    AuthorizationError, AuthorizationContext, default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_expense_api import P6_EXPENSE_API_VERSION, P6ExpenseAPI
from construction_pm.p6_expense_repository import (
    P6Expense,
    P6ExpenseApplicationService,
    SQLiteP6ExpenseRepository,
)


def expense(scope, expense_id="e-1", wbs_id="wbs-1"):
    return P6Expense(
        scope, expense_id, "Temporary facilities", "SITE", "a-1", wbs_id,
        "2026-09-15", Decimal("1200.50"), Decimal("400.25"), Decimal("800.25"),
        "USD", "stored period expense",
    )


def auth(tenant="t1", project="p1", roles=("planner",)):
    return AuthorizationContext(tenant, project, "u1", frozenset(roles))


def api(connection):
    repo = SQLiteP6ExpenseRepository(connection)
    return P6ExpenseAPI(
        P6ExpenseApplicationService(repo, SQLiteTransactionManager(connection)),
        default_project_policy(),
    )


def test_p6_expense_api_round_trip_preserves_decimal_wire_values():
    import sqlite3
    connection = sqlite3.connect(":memory:")
    service = api(connection)
    scope = BackendScope("t1", "p1", 1)

    created = service.create(expense(scope), auth_context=auth())
    assert created["contract_version"] == P6_EXPENSE_API_VERSION
    assert created["expense"]["planned_cost"] == "1200.50"

    result = service.get(scope, "e-1", auth_context=auth())
    assert result == created


def test_p6_expense_api_rejects_cross_scope_and_read_write_permissions():
    import sqlite3
    connection = sqlite3.connect(":memory:")
    service = api(connection)
    scope = BackendScope("t1", "p1", 1)
    service.create(expense(scope), auth_context=auth())

    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        service.get(scope, "e-1", auth_context=auth(tenant="other"))

    with pytest.raises(AuthorizationError):
        service.create(expense(scope), auth_context=auth(roles=("viewer",)))


class WbsScopedPolicy:
    def __init__(self):
        self.base = default_project_policy()

    def is_allowed(self, context, permission):
        return self.base.is_allowed(context, permission)

    def is_allowed_for_wbs(self, context, permission, wbs_id):
        return wbs_id != "wbs-restricted" and self.base.is_allowed(context, permission)


def test_p6_expense_api_enforces_wbs_scope_and_hides_inaccessible_records():
    import sqlite3
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6ExpenseRepository(connection)
    service = P6ExpenseAPI(
        P6ExpenseApplicationService(repository, SQLiteTransactionManager(connection)),
        WbsScopedPolicy(),
    )
    scope = BackendScope("t1", "p1", 1)
    visible = expense(scope, "e-visible", "wbs-visible")
    restricted = expense(scope, "e-restricted", "wbs-restricted")

    created = service.create(visible, auth_context=auth())
    repository.upsert(restricted)

    assert created["expense"]["expense_id"] == "e-visible"
    assert service.get(scope, "e-restricted", auth_context=auth()) is None
    assert [item["expense"]["expense_id"] for item in service.list(scope, auth_context=auth())] == [
        "e-visible"
    ]
    with pytest.raises(AuthorizationError):
        service.create(restricted, auth_context=auth())
    connection.close()
