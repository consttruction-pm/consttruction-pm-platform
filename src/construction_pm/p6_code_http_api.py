from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .backend_p0.models import BackendScope
from .p6_code_repository import P6CodeApplicationService, P6CodeDefinition

P6_CODE_API_VERSION = "p6-code-api.v1"

def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate(); auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")

def _require_permission(policy: AuthorizationPolicy, auth_context: AuthorizationContext, permission: Permission) -> None:
    if not policy.is_allowed(auth_context, permission):
        raise AuthorizationError(f"authorization denied for permission={permission.value}")

def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {"tenant_id": scope.tenant_id, "project_id": scope.project_id, "project_revision": scope.project_revision}

def _dto(definition: P6CodeDefinition) -> dict[str, Any]:
    return {"contract_version": P6_CODE_API_VERSION, "kind": "p6_code", "scope": _scope_dto(definition.scope),
            "code": {"code_id": definition.code_id, "name": definition.name, "subject_area": definition.subject_area,
                     "scope_kind": definition.scope_kind, "scope_key": definition.scope_key,
                     "values": [{"value_id": v.value_id, "value": v.value, "description": v.description} for v in definition.values]}}

@dataclass(frozen=True)
class P6CodeAPI:
    service: P6CodeApplicationService
    authorization_policy: AuthorizationPolicy

    def create(self, definition: P6CodeDefinition, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        _require_scope(definition.scope, auth_context); _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        return _dto(self.service.save(definition))

    def get(self, scope: BackendScope, code_id: str, *, auth_context: AuthorizationContext) -> dict[str, Any] | None:
        _require_scope(scope, auth_context); _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        result = self.service.read(scope, code_id)
        return None if result is None else _dto(result)

    def list(self, scope: BackendScope, *, subject_area: str | None = None, auth_context: AuthorizationContext) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context); _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        return tuple(_dto(item) for item in self.service.list(scope, subject_area=subject_area))

__all__ = ["P6_CODE_API_VERSION", "P6CodeAPI"]
