from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pytest

from construction_pm.application.authorization import AuthorizationContext, AuthorizationError, default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_financial_period_repository import (
    P6FinancialPeriod,
    P6FinancialPeriodApplicationService,
    SQLiteP6FinancialPeriodRepository,
)
from construction_pm.p6_financial_period_api import (
    P6_FINANCIAL_PERIOD_API_VERSION,
    P6FinancialPeriodAPI,
)


class TransactionManager:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self):
        try:
            yield
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("t1", "p1", revision)


def auth(*, tenant_id: str = "t1", project_id: str = "p1", role: str = "planner") -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id=tenant_id,
        project_id=project_id,
        user_id="u1",
        roles=frozenset({role}),
    )


def period(period_id: str = "2026-09") -> P6FinancialPeriod:
    return P6FinancialPeriod(scope(), period_id, "September 2026", "2026-09-01", "2026-09-30", "OPEN")


def api() -> P6FinancialPeriodAPI:
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6FinancialPeriodRepository(connection)
    service = P6FinancialPeriodApplicationService(repository, TransactionManager(connection))
    return P6FinancialPeriodAPI(service, default_project_policy())


def test_versioned_typed_create_get_and_list_boundary() -> None:
    schema_path = Path(__file__).parents[1] / "shared/contracts/p6-financial-period-api.v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert P6_FINANCIAL_PERIOD_API_VERSION == schema["properties"]["contract_version"]["const"]
    instance = api()
    created = instance.create(period(), auth_context=auth())
    assert created["contract_version"] == P6_FINANCIAL_PERIOD_API_VERSION
    assert created["kind"] == "p6_financial_period"
    assert created["financial_period"]["status"] == "OPEN"
    assert instance.get(scope(), "2026-09", auth_context=auth()) == created
    assert instance.list(scope(), auth_context=auth()) == (created,)


def test_cross_scope_and_missing_permission_are_rejected() -> None:
    instance = api()
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        instance.create(period(), auth_context=auth(tenant_id="other"))
    with pytest.raises(AuthorizationError, match="authorization denied"):
        instance.get(scope(), "2026-09", auth_context=auth(role="writer"))
