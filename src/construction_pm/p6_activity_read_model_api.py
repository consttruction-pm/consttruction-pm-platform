from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .backend_p0.models import BackendScope
from .p6_activity_read_model import P6_ACTIVITY_READ_MODEL_VERSION, P6ActivityReadModelService


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


@dataclass(frozen=True)
class P6ActivityReadModelAPI:
    service: P6ActivityReadModelService
    authorization_policy: AuthorizationPolicy

    def get(
        self,
        scope: BackendScope,
        activity_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("authorization denied for permission=project.read")
        result = self.service.read(scope, activity_id)
        return {
            "contract_version": P6_ACTIVITY_READ_MODEL_VERSION,
            "kind": "p6_activity_read_model",
            "scope": {
                "tenant_id": result.scope.tenant_id,
                "project_id": result.scope.project_id,
                "project_revision": result.scope.project_revision,
            },
            "activity_id": result.activity_id,
            "cost_entries": list(result.cost_entries),
            "actual_entries": list(result.actual_entries),
            "baseline_entries": list(result.baseline_entries),
            "evm": dict(result.evm),
        }


__all__ = ["P6_ACTIVITY_READ_MODEL_VERSION", "P6ActivityReadModelAPI"]
