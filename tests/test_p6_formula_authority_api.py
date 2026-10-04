from __future__ import annotations

import sqlite3

import pytest

from construction_pm.application.authorization import AuthorizationContext, AuthorizationError, default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_field_registry import get_field
from construction_pm.p6_field_registry_repository import (
    P6FieldRegistryApplicationService,
    PersistedP6Field,
    SQLiteP6FieldRegistryRepository,
)
from construction_pm.p6_formula_authority_api import (
    P6FormulaAuthorityAPI,
    P6_FORMULA_AUTHORITY_API_VERSION,
)


def _api() -> P6FormulaAuthorityAPI:
    connection = sqlite3.connect(":memory:")
    service = P6FieldRegistryApplicationService(
        SQLiteP6FieldRegistryRepository(connection),
        SQLiteTransactionManager(connection),
    )
    scope = BackendScope("tenant-a", "project-a", 2)
    service.save_field(PersistedP6Field(scope, "p6-field-registry.v1", get_field("activity.activity_id")))
    service.save_field(PersistedP6Field(scope, "p6-field-registry.v1", get_field("activity.percent_complete")))
    return P6FormulaAuthorityAPI(service, default_project_policy())


def _auth(role: str, tenant: str = "tenant-a", project: str = "project-a") -> AuthorizationContext:
    return AuthorizationContext(tenant, project, "user-a", frozenset({role}))


def test_validate_returns_versioned_authoritative_contract() -> None:
    result = _api().validate(
        BackendScope("tenant-a", "project-a", 2),
        "p6-field-registry.v1",
        "[activity.percent_complete] + 1",
        auth_context=_auth("viewer"),
    )
    assert result == {
        "contract_version": P6_FORMULA_AUTHORITY_API_VERSION,
        "validation": {"valid": True, "error_code": None, "message_key": None},
        "dependencies": {"field_ids": ["activity.percent_complete"]},
        "result_type": {"data_type": "double"},
    }


def test_validate_returns_structured_invalid_result() -> None:
    result = _api().validate(
        BackendScope("tenant-a", "project-a", 2),
        "p6-field-registry.v1",
        "[missing.field] + 1",
        auth_context=_auth("viewer"),
    )
    assert result["contract_version"] == P6_FORMULA_AUTHORITY_API_VERSION
    assert result["validation"]["valid"] is False
    assert result["validation"]["error_code"]


def test_validate_rejects_self_reference() -> None:
    result = _api().validate(
        BackendScope("tenant-a", "project-a", 2),
        "p6-field-registry.v1",
        "1 + [activity.percent_complete]",
        auth_context=_auth("viewer"),
        context_field_id="activity.percent_complete",
    )
    assert result["validation"]["error_code"] == "FORMULA_SELF_REFERENCE"


def test_validate_enforces_project_scope_and_read_permission() -> None:
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        _api().validate(
            BackendScope("tenant-b", "project-a", 2),
            "p6-field-registry.v1",
            "1 + 1",
            auth_context=_auth("viewer"),
        )

    with pytest.raises(AuthorizationError, match="authorization denied"):
        _api().validate(
            BackendScope("tenant-a", "project-a", 2),
            "p6-field-registry.v1",
            "1 + 1",
            auth_context=AuthorizationContext(
                "tenant-a", "project-a", "user-a", frozenset({"unknown"})
            ),
        )
