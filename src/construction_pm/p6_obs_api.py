"""Versioned API over the enterprise responsibility-structure hierarchy."""

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
from .p6_obs_repository import P6OBSApplicationService, P6OBSNode

P6_OBS_NODE_API_VERSION = "p6-obs-node-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if (
        scope.tenant_id != auth_context.tenant_id
        or scope.project_id != auth_context.project_id
    ):
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_permission(
    policy: AuthorizationPolicy,
    auth_context: AuthorizationContext,
    permission: Permission,
) -> None:
    if not policy.is_allowed(auth_context, permission):
        raise AuthorizationError(
            f"authorization denied for permission={permission.value}"
        )


def _dto(node: P6OBSNode) -> dict[str, Any]:
    return {
        "contract_version": P6_OBS_NODE_API_VERSION,
        "kind": "p6_obs_node",
        "obs_node": {
            "obs_id": node.obs_id,
            "parent_obs_id": node.parent_obs_id,
            "code": node.code,
            "name": node.name,
            "manager_user_id": node.manager_user_id,
            "sequence_number": node.sequence_number,
        },
    }


@dataclass(frozen=True)
class P6OBSNodeAPI:
    """Scoped API over the tenant-wide responsibility-structure store."""

    service: P6OBSApplicationService
    authorization_policy: AuthorizationPolicy

    def save(
        self, node: P6OBSNode, *, auth_context: AuthorizationContext
    ) -> dict[str, Any]:
        _require_permission(
            self.authorization_policy, auth_context, Permission.P6_OBS_ADMIN
        )
        if node.tenant_id != auth_context.tenant_id:
            raise AuthorizationError("CROSS_SCOPE_ACCESS")
        return _dto(self.service.save(node))

    def get(
        self,
        scope: BackendScope,
        obs_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_permission(
            self.authorization_policy, auth_context, Permission.PROJECT_READ
        )
        node = self.service.read(auth_context.tenant_id, obs_id)
        return None if node is None else _dto(node)

    def list(
        self, scope: BackendScope, *, auth_context: AuthorizationContext
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        _require_permission(
            self.authorization_policy, auth_context, Permission.PROJECT_READ
        )
        return {
            "contract_version": P6_OBS_NODE_API_VERSION,
            "obs_nodes": [
                _dto(node)["obs_node"]
                for node in self.service.list(auth_context.tenant_id)
            ],
        }


__all__ = ["P6_OBS_NODE_API_VERSION", "P6OBSNodeAPI"]
