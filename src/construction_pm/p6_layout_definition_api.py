from __future__ import annotations

from typing import Any

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .backend_p0.models import BackendScope
from .p6_layout_definition_repository import PersistedP6Layout, P6LayoutRepository

P6_LAYOUT_DEFINITION_API_VERSION = "p6-layout-definition-api.v1"

def _require_scope(scope: BackendScope, auth: AuthorizationContext) -> None:
    scope.validate()
    auth.validate()
    if scope.tenant_id != auth.tenant_id or scope.project_id != auth.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")

def _dto(layout: PersistedP6Layout) -> dict[str, Any]:
    return {
        "contract_version": P6_LAYOUT_DEFINITION_API_VERSION,
        "kind": "layout_definition",
        "scope": {"tenant_id": layout.scope.tenant_id, "project_id": layout.scope.project_id, "project_revision": layout.scope.project_revision},
        "layout": {
            "schema_version": layout.schema_version,
            "scope": layout.layout_scope,
            "view_id": layout.view_id,
            "revision": layout.revision,
            "columns": [c.__dict__ for c in layout.columns],
            "metadata": dict(layout.metadata),
        },
    }

class P6LayoutDefinitionAPI:
    def __init__(self, repository: P6LayoutRepository, authorization_policy: AuthorizationPolicy) -> None:
        self.repository = repository
        self.authorization_policy = authorization_policy

    def save(
        self,
        layout: PersistedP6Layout,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(layout.scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
            raise AuthorizationError("authorization denied")
        return _dto(self.repository.upsert(layout))

    def get(self, scope: BackendScope, layout_scope: str, view_id: str, *, auth_context: AuthorizationContext) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("authorization denied")
        layout = self.repository.get(scope, layout_scope, view_id)
        return None if layout is None else _dto(layout)

__all__ = ["P6_LAYOUT_DEFINITION_API_VERSION", "P6LayoutDefinitionAPI"]
