from __future__ import annotations

import sqlite3

import pytest

from construction_pm.application.authorization import AuthorizationContext, AuthorizationError, default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_field_registry import get_field, P6FieldType
from construction_pm.p6_field_registry_api import P6FieldRegistryAPI, P6_FIELD_REGISTRY_API_VERSION
from construction_pm.p6_field_registry_repository import P6FieldRegistryApplicationService, SQLiteP6FieldRegistryRepository
from construction_pm.p6_user_defined_fields_repository import (
    P6UserDefinedFieldApplicationService,
    P6UserDefinedFieldDefinition,
    SQLiteP6UserDefinedFieldRepository,
)


def _api() -> P6FieldRegistryAPI:
    connection = sqlite3.connect(":memory:")
    return P6FieldRegistryAPI(
        field_service=P6FieldRegistryApplicationService(
            SQLiteP6FieldRegistryRepository(connection), SQLiteTransactionManager(connection)
        ),
        udf_service=P6UserDefinedFieldApplicationService(
            SQLiteP6UserDefinedFieldRepository(connection), SQLiteTransactionManager(connection)
        ),
        authorization_policy=default_project_policy(),
    )


def _auth(role: str, tenant: str = "tenant-a", project: str = "project-a") -> AuthorizationContext:
    return AuthorizationContext(tenant, project, "user-a", frozenset({role}))


def _udf() -> P6UserDefinedFieldDefinition:
    return P6UserDefinedFieldDefinition(
        scope=BackendScope("tenant-a", "project-a", 2),
        registry_version="p6-field-registry.v1",
        udf_id="udf.activity.contract_status",
        subject_area="Activity",
        display_name="Contract Status",
        data_type=P6FieldType.ENUM,
        nullable=False,
        allowed_values=("draft", "active"),
    )


def test_field_api_returns_versioned_typed_contract() -> None:
    api = _api()
    scope = BackendScope("tenant-a", "project-a", 2)
    result = api.save_field(scope, "p6-field-registry.v1", get_field("activity.activity_id"), auth_context=_auth("planner"))

    assert result["contract_version"] == P6_FIELD_REGISTRY_API_VERSION
    assert result["field"]["data_type"] == "string"
    assert result["scope"]["project_revision"] == 2


def test_udf_api_returns_typed_definition() -> None:
    api = _api()
    result = api.save_udf(_udf(), auth_context=_auth("planner"))

    assert result["kind"] == "user_defined_field"
    assert result["udf"]["data_type"] == "enum"
    assert result["udf"]["allowed_values"] == ["draft", "active"]


def test_api_rejects_cross_scope_access() -> None:
    api = _api()
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        api.get_field(
            BackendScope("tenant-b", "project-a", 2),
            "p6-field-registry.v1",
            "activity.activity_id",
            auth_context=_auth("viewer"),
        )


def test_api_rejects_read_without_permission() -> None:
    api = _api()
    with pytest.raises(AuthorizationError, match="authorization denied"):
        api.get_field(
            BackendScope("tenant-a", "project-a", 2),
            "p6-field-registry.v1",
            "activity.activity_id",
            auth_context=AuthorizationContext("tenant-a", "project-a", "user-a", frozenset({"unknown"})),
        )


def test_api_rejects_write_for_viewer() -> None:
    api = _api()
    with pytest.raises(AuthorizationError, match="authorization denied"):
        api.save_udf(_udf(), auth_context=_auth("viewer"))


def test_api_lists_fields_and_udfs_deterministically() -> None:
    api = _api()
    scope = BackendScope("tenant-a", "project-a", 2)
    api.save_field(scope, "p6-field-registry.v1", get_field("activity.activity_name"), auth_context=_auth("planner"))
    api.save_field(scope, "p6-field-registry.v1", get_field("activity.activity_id"), auth_context=_auth("planner"))
    api.save_udf(_udf(), auth_context=_auth("planner"))

    fields = api.list_fields(scope, "p6-field-registry.v1", "Activity", auth_context=_auth("viewer"))
    udfs = api.list_udfs(scope, "p6-field-registry.v1", "Activity", auth_context=_auth("viewer"))

    assert [item["field"]["field_id"] for item in fields] == [
        "activity.activity_id",
        "activity.activity_name",
    ]
    assert [item["udf"]["udf_id"] for item in udfs] == ["udf.activity.contract_status"]
