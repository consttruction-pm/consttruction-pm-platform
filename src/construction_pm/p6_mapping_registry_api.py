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
from .p6_mapping_registry import (
    P6MappingFormat,
    P6MappingRegistryApplicationService,
    P6MappingStatus,
    PersistedP6Mapping,
)

P6_MAPPING_REGISTRY_API_VERSION = "p6-mapping-registry-api.v1"


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
class P6MappingRegistryAPI:
    service: P6MappingRegistryApplicationService
    authorization_policy: AuthorizationPolicy

    def create(
        self,
        record: PersistedP6Mapping,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(record.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        return _dto(self.service.save_mapping(record))

    def get(
        self,
        scope: BackendScope,
        mapping_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        result = self.service.read_mapping(scope, mapping_id)
        return None if result is None else _dto(result)

    def list(
        self,
        scope: BackendScope,
        *,
        format: P6MappingFormat | None = None,
        subject_area: str | None = None,
        status: P6MappingStatus | None = None,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        results = self.service.list_mappings(
            scope,
            format=format,
            subject_area=subject_area,
        )
        if status is not None:
            results = tuple(
                item for item in results if item.definition.status is status
            )
        return tuple(_dto(item) for item in results)


def _dto(record: PersistedP6Mapping) -> dict[str, Any]:
    definition = record.definition
    return {
        "contract_version": P6_MAPPING_REGISTRY_API_VERSION,
        "kind": "p6_mapping",
        "scope": {
            "tenant_id": record.scope.tenant_id,
            "project_id": record.scope.project_id,
            "project_revision": record.scope.project_revision,
        },
        "mapping": {
            "mapping_id": definition.mapping_id,
            "registry_version": definition.registry_version,
            "format": definition.format.value,
            "subject_area": definition.subject_area,
            "source_field": definition.source_field,
            "canonical_field": definition.canonical_field,
            "status": definition.status.value,
            "source_type": definition.source_type,
            "canonical_type": definition.canonical_type,
            "unit": definition.unit,
            "notes": definition.notes,
        },
    }


__all__ = ["P6_MAPPING_REGISTRY_API_VERSION", "P6MappingRegistryAPI"]
