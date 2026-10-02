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
from .p6_baseline_repository import P6Baseline, P6BaselineApplicationService

P6_BASELINE_API_VERSION = "p6-baseline-api.v1"


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


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _dto(baseline: P6Baseline) -> dict[str, Any]:
    return {
        "contract_version": P6_BASELINE_API_VERSION,
        "kind": "p6_baseline",
        "scope": _scope_dto(baseline.scope),
        "baseline": {
            "baseline_id": baseline.baseline_id,
            "name": baseline.name,
            "baseline_type": baseline.baseline_type,
            "source_revision": baseline.source_revision,
            "created_at": baseline.created_at,
            "notes": baseline.notes,
        },
    }


@dataclass(frozen=True)
class P6BaselineAPI:
    """Typed transport boundary over authoritative baseline persistence."""

    service: P6BaselineApplicationService
    authorization_policy: AuthorizationPolicy

    def create(
        self,
        baseline: P6Baseline,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(baseline.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        return _dto(self.service.save(baseline))

    def get(
        self,
        scope: BackendScope,
        baseline_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        result = self.service.read(scope, baseline_id)
        return None if result is None else _dto(result)

    def list(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        return tuple(_dto(item) for item in self.service.list(scope))


__all__ = ["P6_BASELINE_API_VERSION", "P6BaselineAPI"]
