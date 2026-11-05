from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .backend_p0.models import BackendScope
from .p6_activity_step_repository import P6ActivityStep, P6ActivityStepApplicationService

P6_ACTIVITY_STEP_API_VERSION = "p6-activity-step-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_read(policy: AuthorizationPolicy, auth_context: AuthorizationContext) -> None:
    if not policy.is_allowed(auth_context, Permission.PROJECT_READ):
        raise AuthorizationError("authorization denied for permission=project.read")


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _dto(step: P6ActivityStep) -> dict[str, Any]:
    return {
        "contract_version": P6_ACTIVITY_STEP_API_VERSION,
        "kind": "p6_activity_step",
        "scope": _scope_dto(step.scope),
        "step": {
            "step_id": step.step_id,
            "activity_id": step.activity_id,
            "sequence": step.sequence,
            "description": step.description,
            "weight": None if step.weight is None else str(step.weight),
            "start_date": step.start_date,
            "finish_date": step.finish_date,
            "udf_values": [{"field_id": key, "value": value} for key, value in step.udf_values],
        },
    }


@dataclass(frozen=True)
class P6ActivityStepAPI:
    """Authenticated read boundary for immutable, revision-scoped Activity Steps."""

    service: P6ActivityStepApplicationService
    authorization_policy: AuthorizationPolicy

    def get(
        self,
        scope: BackendScope,
        step_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_read(self.authorization_policy, auth_context)
        step = self.service.read(scope, step_id)
        return None if step is None else _dto(step)

    def list(
        self,
        scope: BackendScope,
        *,
        activity_id: str | None = None,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_read(self.authorization_policy, auth_context)
        return tuple(_dto(step) for step in self.service.list(scope, activity_id=activity_id))


__all__ = ["P6_ACTIVITY_STEP_API_VERSION", "P6ActivityStepAPI"]
