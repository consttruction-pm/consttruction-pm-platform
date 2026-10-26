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
    service.save_field(PersistedP6Field(scope, "p6-field-registry.v1", get_field("activity.planned_duration")))
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


def test_unrepresented_registry_field_does_not_poison_unrelated_validation() -> None:
    # activity.planned_duration is registered but has no safe formula
    # representation; a formula that does not reference it must still validate.
    result = _api().validate(
        BackendScope("tenant-a", "project-a", 2),
        "p6-field-registry.v1",
        "[activity.percent_complete] / 100",
        auth_context=_auth("viewer"),
    )
    assert result["validation"] == {
        "valid": True,
        "error_code": None,
        "message_key": None,
    }
    assert result["dependencies"]["field_ids"] == ["activity.percent_complete"]
    assert result["result_type"]["data_type"] == "double"


def test_validate_returns_structured_error_for_unrepresented_field() -> None:
    result = _api().validate(
        BackendScope("tenant-a", "project-a", 2),
        "p6-field-registry.v1",
        "[activity.planned_duration] * 2",
        auth_context=_auth("viewer"),
    )
    assert result["validation"] == {
        "valid": False,
        "error_code": "UNSUPPORTED_P6_FORMULA_FIELD_TYPE:duration",
        "message_key": "p6.formula.validation.error",
    }
    assert result["dependencies"]["field_ids"] == []
    assert result["result_type"]["data_type"] is None


def test_self_reference_precedes_unrepresented_field_diagnostic() -> None:
    result = _api().validate(
        BackendScope("tenant-a", "project-a", 2),
        "p6-field-registry.v1",
        "[activity.planned_duration] + 1",
        auth_context=_auth("viewer"),
        context_field_id="activity.planned_duration",
    )
    assert result["validation"]["error_code"] == "FORMULA_SELF_REFERENCE"
    assert result["result_type"]["data_type"] is None


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
