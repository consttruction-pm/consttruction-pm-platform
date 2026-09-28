from __future__ import annotations

import sqlite3

import pytest

from construction_pm.application.authorization import AuthorizationContext, AuthorizationError, default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_formula_definition_api import P6FormulaDefinitionAPI, P6_FORMULA_DEFINITION_API_VERSION
from construction_pm.p6_formula_definition_repository import (
    FormulaDefinitionCreateRequest,
    P6FormulaDefinitionApplicationService,
    SQLiteP6FormulaDefinitionRepository,
)
from construction_pm.p6_formula_engine import FormulaType


def api() -> P6FormulaDefinitionAPI:
    connection = sqlite3.connect(":memory:")
    return P6FormulaDefinitionAPI(
        P6FormulaDefinitionApplicationService(
            SQLiteP6FormulaDefinitionRepository(connection), SQLiteTransactionManager(connection)
        ),
        default_project_policy(),
    )


def auth(role: str, tenant: str = "tenant-a", project: str = "project-a") -> AuthorizationContext:
    return AuthorizationContext(tenant, project, "user-a", frozenset({role}))


def request() -> FormulaDefinitionCreateRequest:
    return FormulaDefinitionCreateRequest(
        scope=BackendScope("tenant-a", "project-a", 3),
        semantic_version="p6-formula.v1",
        semantic_reference="shared-core:p6-formula",
        formula_id="activity.total",
        version="1.0",
        expression="[activity.qty] * [activity.rate]",
        result_type=FormulaType.NUMBER,
        result_unit="m3",
        dependencies=("activity.qty", "activity.rate"),
        metadata={"futureField": {"preserve": True}},
    )


def test_formula_api_returns_versioned_typed_contract() -> None:
    service = api()
    result = service.create(request(), auth_context=auth("planner"))
    assert result["contract_version"] == P6_FORMULA_DEFINITION_API_VERSION
    assert result["formula"]["result_type"] == "number"
    assert result["formula"]["dependencies"] == ["activity.qty", "activity.rate"]
    assert result["formula"]["metadata"]["futureField"] == {"preserve": True}


def test_formula_api_rejects_cross_scope_access() -> None:
    service = api()
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        service.get(
            BackendScope("tenant-b", "project-a", 3),
            "activity.total",
            "1.0",
            auth_context=auth("viewer"),
        )


def test_formula_api_rejects_viewer_write() -> None:
    service = api()
    with pytest.raises(AuthorizationError, match="authorization denied"):
        service.create(request(), auth_context=auth("viewer"))
