from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .backend_p0.models import BackendScope
from .p6_mapping_registry import P6MappingDefinition, P6MappingFormat, P6MappingRegistryApplicationService, P6MappingStatus, PersistedP6Mapping

P6_MAPPING_API_VERSION = "p6-mapping-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate(); auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_permission(policy: AuthorizationPolicy, auth_context: AuthorizationContext, permission: Permission) -> None:
    if not policy.is_allowed(auth_context, permission):
        raise AuthorizationError(f"authorization denied for permission={permission.value}")


def _dto(record: PersistedP6Mapping) -> dict[str, Any]:
    d = record.definition
    return {
        "contract_version": P6_MAPPING_API_VERSION,
        "kind": "p6_mapping",
        "scope": {"tenant_id": record.scope.tenant_id, "project_id": record.scope.project_id, "project_revision": record.scope.project_revision},
        "mapping": {
            "mapping_id": d.mapping_id, "registry_version": d.registry_version,
            "format": d.format.value, "subject_area": d.subject_area,
            "source_field": d.source_field, "canonical_field": d.canonical_field,
            "status": d.status.value, "source_type": d.source_type,
            "canonical_type": d.canonical_type, "unit": d.unit, "notes": d.notes,
        },
    }


@dataclass(frozen=True)
class P6MappingAPI:
    service: P6MappingRegistryApplicationService
    authorization_policy: AuthorizationPolicy

    def create(self, record: PersistedP6Mapping, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        _require_scope(record.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        return _dto(self.service.save_mapping(record))

    def get(self, scope: BackendScope, mapping_id: str, *, auth_context: AuthorizationContext) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        result = self.service.read_mapping(scope, mapping_id)
        return None if result is None else _dto(result)

    def list(self, scope: BackendScope, *, format: P6MappingFormat | None = None, subject_area: str | None = None, auth_context: AuthorizationContext) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        return tuple(_dto(x) for x in self.service.list_mappings(scope, format, subject_area))


__all__ = ["P6_MAPPING_API_VERSION", "P6MappingAPI"]
