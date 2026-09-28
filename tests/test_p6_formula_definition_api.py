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


def test_formula_api_records_immutable_audit_event() -> None:
    service = api()
    created = service.create(request(), auth_context=auth("planner"))
    events = service.list_audit(
        BackendScope("tenant-a", "project-a", 3),
        "activity.total",
        auth_context=auth("viewer"),
    )
    assert len(events) == 1
    assert events[0]["formula_version"] == created["formula"]["version"]
    assert events[0]["actor_id"] == "user-a"
    assert events[0]["action"] == "create"
    assert events[0]["semantic_version"] == "p6-formula.v1"
    assert events[0]["expression_sha256"] == expression_sha256(request().expression)


def test_formula_api_same_immutable_version_does_not_duplicate_audit() -> None:
    service = api()
    service.create(request(), auth_context=auth("planner"))
    service.create(request(), auth_context=auth("planner"))
    events = service.list_audit(
        BackendScope("tenant-a", "project-a", 3),
        "activity.total",
        auth_context=auth("viewer"),
    )
    assert len(events) == 1


def test_formula_api_creates_a_distinct_audit_event_for_new_version() -> None:
    service = api()
    first = request()
    service.create(first, auth_context=auth("planner"))
    second = FormulaDefinitionCreateRequest(
        scope=first.scope,
        semantic_version=first.semantic_version,
        semantic_reference=first.semantic_reference,
        formula_id=first.formula_id,
        version="2.0",
        expression="[activity.qty] * [activity.rate] + [activity.waste]",
        result_type=first.result_type,
        result_unit=first.result_unit,
        dependencies=first.dependencies + ("activity.waste",),
        metadata=first.metadata,
    )
    service.create(second, auth_context=auth("planner"))
    events = service.list_audit(
        first.scope,
        first.formula_id,
        auth_context=auth("viewer"),
    )
    assert [event["formula_version"] for event in events] == ["1.0", "2.0"]
