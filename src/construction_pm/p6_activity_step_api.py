"""Versioned read boundary for activity step child records."""

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
from .p6_activity_step_repository import (
    P6ActivityStep,
    P6ActivityStepApplicationService,
    P6ActivityStepPersistenceError,
)

P6_ACTIVITY_STEP_READ_API_VERSION = "p6-activity-step-read-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _step_dto(step: P6ActivityStep) -> dict[str, Any]:
    return {
        "step_id": step.step_id,
        "activity_id": step.activity_id,
        "sequence": step.sequence,
        "description": step.description,
        "weight": None if step.weight is None else str(step.weight),
        "start_date": step.start_date,
        "finish_date": step.finish_date,
        "udf_values": {key: value for key, value in step.udf_values},
    }


@dataclass(frozen=True)
class P6ActivityStepReadAPI:
    """Read-only activity steps with revision and permission enforcement."""

    service: P6ActivityStepApplicationService
    authorization_policy: AuthorizationPolicy

    def list(
        self,
        scope: BackendScope,
        activity_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("ACTIVITY_STEP_READ_NOT_AUTHORIZED")
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise P6ActivityStepPersistenceError("INVALID_ACTIVITY_ID")
        steps = self.service.list(scope, activity_id)
        # The stored order is authoritative: sequence, then step id.
        return {
            "contract_version": P6_ACTIVITY_STEP_READ_API_VERSION,
            "kind": "p6_activity_step_list",
            "scope": _scope_dto(scope),
            "activity_id": activity_id,
            "steps": [_step_dto(step) for step in steps],
        }


__all__ = ["P6_ACTIVITY_STEP_READ_API_VERSION", "P6ActivityStepReadAPI"]
