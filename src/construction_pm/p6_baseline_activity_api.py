from __future__ import annotations

"""Read boundary for the immutable activity windows stored in a baseline.

The Gantt draws a baseline bar from the *stored* planned window of each activity.
This module exposes that read through the existing baseline activity repository;
it never calculates, shifts or fills a baseline date.
"""

from dataclasses import dataclass
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_baseline_activity_repository import P6BaselineActivityRepository
from .p6_baseline_repository import P6BaselineRepository

P6_BASELINE_ACTIVITY_API_VERSION = "p6-baseline-activity-api.v1"


class P6BaselineActivityReadError(ValueError):
    """Raised when the requested baseline window cannot be served."""


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


def _identifier(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or "/" in value:
        raise P6BaselineActivityReadError("BASELINE_ACTIVITY_ID_INVALID")
    return value


def _activity_dto(activity: object) -> dict[str, Any]:
    return {
        "activity_id": activity.activity_id,
        "planned_start": activity.planned_start.isoformat(),
        "planned_finish": activity.planned_finish.isoformat(),
        "budgeted_cost": str(activity.budgeted_cost),
        "currency": activity.currency,
        "wbs_id": activity.wbs_id,
        "earned_value_technique": activity.earned_value_technique,
    }


@dataclass(frozen=True)
class P6BaselineActivityAPI:
    """Read-only transport over the persisted baseline activity windows."""

    repository: P6BaselineActivityRepository
    baseline_repository: P6BaselineRepository
    authorization_policy: AuthorizationPolicy

    def list(
        self,
        scope: BackendScope,
        baseline_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        _require_permission(
            self.authorization_policy, auth_context, Permission.PROJECT_READ
        )
        identifier = _identifier(baseline_id)
        if self.baseline_repository.get(scope, identifier) is None:
            raise P6BaselineActivityReadError("BASELINE_NOT_FOUND")
        rows = sorted(self.repository.list(scope, identifier), key=lambda row: row.activity_id)
        return {
            "contract_version": P6_BASELINE_ACTIVITY_API_VERSION,
            "kind": "p6_baseline_activity_list",
            "scope": {
                "tenant_id": scope.tenant_id,
                "project_id": scope.project_id,
                "project_revision": scope.project_revision,
            },
            "baseline_id": identifier,
            "activities": [_activity_dto(row) for row in rows],
        }


__all__ = [
    "P6_BASELINE_ACTIVITY_API_VERSION",
    "P6BaselineActivityAPI",
    "P6BaselineActivityReadError",
]
