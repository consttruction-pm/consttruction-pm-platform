from decimal import Decimal

import pytest

from construction_pm.application.authorization import AuthorizationError, AuthorizationContext, default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_expense_api import P6_EXPENSE_API_VERSION, P6ExpenseAPI
from construction_pm.p6_expense_repository import (
    P6Expense,
    P6ExpenseApplicationService,
    SQLiteP6ExpenseRepository,
)


def expense(scope):
    return P6Expense(
        scope, "e-1", "Temporary facilities", "SITE", "a-1", "wbs-1",
        "2026-09-15", Decimal("1200.50"), Decimal("400.25"), Decimal("800.25"),
        "USD", "stored period expense",
    )


def auth(tenant="t1", project="p1", permissions=("project.read", "project.write")):
    return AuthorizationContext("u1", tenant, project, frozenset(permissions))


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
        service.create(expense(scope), auth_context=auth(permissions=("project.read",)))
