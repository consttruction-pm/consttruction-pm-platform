from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_field_registry import P6FieldDefinition
from .p6_field_registry_repository import (
    P6FieldRegistryApplicationService,
    PersistedP6Field,
)
from .p6_user_defined_fields_repository import (
    P6UserDefinedFieldApplicationService,
    P6UserDefinedFieldDefinition,
)


P6_FIELD_REGISTRY_API_VERSION = "p6-field-registry-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_permission(
    policy: AuthorizationPolicy,
    auth_context: AuthorizationContext,
    permission: Permission,
) -> None:
    if not policy.is_allowed(auth_context, permission):
        raise AuthorizationError(f"authorization denied for permission={permission.value}")


@dataclass(frozen=True)
class P6FieldRegistryAPI:
    field_service: P6FieldRegistryApplicationService
    udf_service: P6UserDefinedFieldApplicationService
    authorization_policy: AuthorizationPolicy

    def save_field(
        self,
        scope: BackendScope,
        registry_version: str,
        field: P6FieldDefinition,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        saved = self.field_service.save_field(
            PersistedP6Field(scope=scope, registry_version=registry_version, field=field)
        )
        return _field_dto(saved)

    def get_field(
        self,
        scope: BackendScope,
        registry_version: str,
        field_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        loaded = self.field_service.read_field(scope, registry_version, field_id)
        return None if loaded is None else _field_dto(loaded)

    def list_fields(
        self,
        scope: BackendScope,
        registry_version: str,
        subject_area: str | None = None,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        return tuple(
            _field_dto(item)
            for item in self.field_service.list_fields(scope, registry_version, subject_area)
        )

    def save_udf(
        self,
        definition: P6UserDefinedFieldDefinition,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(definition.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        return _udf_dto(self.udf_service.save_definition(definition))

    def get_udf(
        self,
        scope: BackendScope,
        registry_version: str,
        udf_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        loaded = self.udf_service.read_definition(scope, registry_version, udf_id)
        return None if loaded is None else _udf_dto(loaded)

    def list_udfs(
        self,
        scope: BackendScope,
        registry_version: str,
        subject_area: str | None = None,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        return tuple(
            _udf_dto(item)
            for item in self.udf_service.list_definitions(scope, registry_version, subject_area)
        )


def _field_dto(record: PersistedP6Field) -> dict[str, Any]:
    return {
        "contract_version": P6_FIELD_REGISTRY_API_VERSION,
        "kind": "field",
        "scope": {
            "tenant_id": record.scope.tenant_id,
            "project_id": record.scope.project_id,
            "project_revision": record.scope.project_revision,
        },
        "registry_version": record.registry_version,
        "field": {
            "field_id": record.field.field_id,
            "subject_area": record.field.subject_area,
            "p6_field": record.field.p6_field,
            "display_name": record.field.display_name,
            "data_type": record.field.data_type.value,
            "writable": record.field.writable,
            "computed": record.field.computed,
            "unit": record.field.unit,
            "reference_url": record.field.reference_url,
            "read_only": record.field.read_only,
            "filterable": record.field.filterable,
            "orderable": record.field.orderable,
            "nullable": record.field.nullable,
            "disposition": record.field.disposition,
        },
    }


def _udf_dto(definition: P6UserDefinedFieldDefinition) -> dict[str, Any]:
    return {
        "contract_version": P6_FIELD_REGISTRY_API_VERSION,
        "kind": "user_defined_field",
        "scope": {
            "tenant_id": definition.scope.tenant_id,
            "project_id": definition.scope.project_id,
            "project_revision": definition.scope.project_revision,
        },
        "registry_version": definition.registry_version,
        "udf": {
            "udf_id": definition.udf_id,
            "subject_area": definition.subject_area,
            "display_name": definition.display_name,
            "data_type": definition.data_type.value,
            "writable": definition.writable,
            "nullable": definition.nullable,
            "unit": definition.unit,
            "allowed_values": list(definition.allowed_values),
        },
    }


__all__ = ["P6_FIELD_REGISTRY_API_VERSION", "P6FieldRegistryAPI"]
