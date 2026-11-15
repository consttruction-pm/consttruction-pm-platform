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


def auth(tenant="t1", project="p1", roles=("planner",)):
    return AuthorizationContext(tenant, project, "u1", frozenset(roles))


def api(connection, wbs_access_repository=None):
    repo = SQLiteP6ExpenseRepository(connection)
    return P6ExpenseAPI(
        P6ExpenseApplicationService(repo, SQLiteTransactionManager(connection)),
        default_project_policy(),
        wbs_access_repository=wbs_access_repository,
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


def test_expense_access_is_scoped_by_responsible_wbs_obs():
    import sqlite3
    connection = sqlite3.connect(":memory:")
    scope = BackendScope("t1", "p1", 1)
    base = api(connection)
    base.create(expense(scope), auth_context=auth())

    class WBSAccess:
        def has_wbs_permission(self, scope, user_id, wbs_id, permission):
            return permission == "project.read"

    scoped = api(connection, WBSAccess())
    assert scoped.get(scope, "e-1", auth_context=auth())["expense"]["wbs_id"] == "wbs-1"
    assert [item["expense"]["expense_id"] for item in scoped.list(scope, auth_context=auth())] == ["e-1"]
    with pytest.raises(AuthorizationError, match="WBS_OBS_ACCESS_DENIED"):
        scoped.create(expense(scope), auth_context=auth())
