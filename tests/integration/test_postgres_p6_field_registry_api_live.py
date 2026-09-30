from __future__ import annotations

import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.application.authorization import AuthorizationContext, default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.p6_field_registry import P6FieldType, get_field
from construction_pm.p6_field_registry_api import P6FieldRegistryAPI
from construction_pm.p6_field_registry_repository import (
    P6FieldRegistryApplicationService,
    PostgresP6FieldRegistryRepository,
)
from construction_pm.p6_user_defined_fields_repository import (
    P6UserDefinedFieldApplicationService,
    P6UserDefinedFieldDefinition,
    PostgresP6UserDefinedFieldRepository,
)


def _scope() -> BackendScope:
    suffix = uuid.uuid4().hex
    return BackendScope(f"api-tenant-{suffix}", f"api-project-{suffix}", 7)


def _auth(scope: BackendScope, role: str = "planner") -> AuthorizationContext:
    return AuthorizationContext(
        scope.tenant_id,
        scope.project_id,
        "api-user",
        frozenset({role}),
    )


def _api(connection: object) -> P6FieldRegistryAPI:
    field_repository = PostgresP6FieldRegistryRepository(connection)
    udf_repository = PostgresP6UserDefinedFieldRepository(connection)
    field_repository.initialize()
    udf_repository.initialize()
    return P6FieldRegistryAPI(
        field_service=P6FieldRegistryApplicationService(
            field_repository,
            PostgresTransactionManager(connection),
        ),
        udf_service=P6UserDefinedFieldApplicationService(
            udf_repository,
            PostgresTransactionManager(connection),
        ),
        authorization_policy=default_project_policy(),
    )


def test_postgres_field_registry_api_persists_typed_field_and_udf_contracts() -> None:
    scope = _scope()
    with psycopg.connect(DSN) as connection:
        api = _api(connection)
        connection.commit()

        field = api.save_field(
            scope,
            "p6-field-registry.v1",
            get_field("activity.activity_id"),
            auth_context=_auth(scope),
        )
        udf = P6UserDefinedFieldDefinition(
            scope=scope,
            registry_version="p6-field-registry.v1",
            udf_id="udf.activity.contract_status",
            subject_area="Activity",
            display_name="Contract Status",
            data_type=P6FieldType.ENUM,
            nullable=False,
            allowed_values=("draft", "active"),
        )
        udf_result = api.save_udf(udf, auth_context=_auth(scope))

        assert field["kind"] == "field"
        assert field["field"]["data_type"] == "string"
        assert field["scope"]["project_revision"] == scope.project_revision
        assert udf_result["kind"] == "user_defined_field"
        assert udf_result["udf"]["data_type"] == "enum"

        assert api.get_field(
            scope,
            "p6-field-registry.v1",
            "activity.activity_id",
            auth_context=_auth(scope, "viewer"),
        ) == field
        assert api.get_udf(
            scope,
            "p6-field-registry.v1",
            udf.udf_id,
            auth_context=_auth(scope, "viewer"),
        ) == udf_result


def test_postgres_field_registry_api_preserves_scope_and_revision_isolation() -> None:
    scope = _scope()
    with psycopg.connect(DSN) as connection:
        api = _api(connection)
        connection.commit()

        api.save_udf(
            P6UserDefinedFieldDefinition(
                scope=scope,
                registry_version="p6-field-registry.v1",
                udf_id="udf.activity.status",
                subject_area="Activity",
                display_name="Status",
                data_type=P6FieldType.ENUM,
                nullable=False,
                allowed_values=("draft", "active"),
            ),
            auth_context=_auth(scope),
        )

        assert api.get_udf(
            BackendScope(scope.tenant_id + "-other", scope.project_id, scope.project_revision),
            "p6-field-registry.v1",
            "udf.activity.status",
            auth_context=AuthorizationContext(
                scope.tenant_id + "-other",
                scope.project_id,
                "api-user",
                frozenset({"viewer"}),
            ),
        ) is None

        with pytest.raises(ValueError, match="REVISION_CONFLICT"):
            api.get_udf(
                BackendScope(scope.tenant_id, scope.project_id, scope.project_revision + 1),
                "p6-field-registry.v1",
                "udf.activity.status",
                auth_context=_auth(
                    BackendScope(scope.tenant_id, scope.project_id, scope.project_revision + 1),
                    "viewer",
                ),
            )
