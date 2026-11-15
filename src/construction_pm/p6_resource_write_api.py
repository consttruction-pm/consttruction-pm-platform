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
from .p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentApplicationService,
    P6ResourceAssignmentPeriodApplicationService,
    P6ResourceAssignmentPeriodValue,
)

P6_RESOURCE_WRITE_API_VERSION = "p6-resource-write-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_activity_permission(
    policy: AuthorizationPolicy,
    auth_context: AuthorizationContext,
    permission: Permission,
    scope: BackendScope,
    activity_id: str,
    activity_repository: Any | None,
) -> None:
    """Authorize a resource fact through its owning Activity Master WBS.

    Profile-backed policies must resolve the activity and evaluate its WBS
    responsibility. They never fall back to a project-wide role or scope hint.
    Legacy role policies without WBS evaluation retain their existing project
    permission behavior.
    """
    scoped = getattr(policy, "is_allowed_for_wbs", None)
    if callable(scoped):
        activity = (
            None
            if activity_repository is None
            else activity_repository.get(scope, activity_id)
        )
        wbs_id = None if activity is None else getattr(activity, "wbs_id", None)
        allowed = bool(
            isinstance(wbs_id, str)
            and wbs_id.strip()
            and scoped(auth_context, permission, wbs_id)
        )
    else:
        allowed = policy.is_allowed(auth_context, permission)
    if not allowed:
        raise AuthorizationError("RESOURCE_WRITE_NOT_AUTHORIZED")


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


@dataclass(frozen=True)
class P6ResourceWriteAPI:
    """Versioned write boundary over authoritative resource persistence."""

    period_service: P6ResourceAssignmentPeriodApplicationService
    authorization_policy: AuthorizationPolicy
    # Legacy role policies can omit Activity Master lookup; profile-backed
    # policies fail closed without it so WBS scope cannot be skipped.
    assignment_service: P6ResourceAssignmentApplicationService | None = None
    activity_repository: Any | None = None

    def save_assignment(
        self,
        value: P6ResourceAssignment,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(value.scope, auth_context)
        _require_activity_permission(
            self.authorization_policy, auth_context, Permission.P6_ACTIVITY_ADMIN,
            value.scope, value.activity_id, self.activity_repository,
        )
        if self.assignment_service is None:
            raise ValueError("RESOURCE_ASSIGNMENT_WRITE_SERVICE_NOT_CONFIGURED")
        stored = self.assignment_service.save(value)
        return _assignment_dto(stored)

    def save_assignment_period(
        self,
        value: P6ResourceAssignmentPeriodValue,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(value.scope, auth_context)
        _require_activity_permission(
            self.authorization_policy, auth_context, Permission.P6_EDIT_PERIOD_PERFORMANCE,
            value.scope, value.activity_id, self.activity_repository,
        )
        stored = self.period_service.save(value)
        return _period_dto(stored)


def _assignment_dto(item: P6ResourceAssignment) -> dict[str, Any]:
    return {
        "contract_version": P6_RESOURCE_WRITE_API_VERSION,
        "kind": "resource_assignment",
        "scope": _scope_dto(item.scope),
        "assignment": {
            "assignment_id": item.assignment_id,
            "activity_id": item.activity_id,
            "resource_id": item.resource_id,
            "role_id": item.role_id,
            "units": item.units,
            "actual_units": item.actual_units,
            "remaining_units": item.remaining_units,
            "planned_cost": item.planned_cost,
            "actual_cost": item.actual_cost,
            "remaining_cost": item.remaining_cost,
            "unit": item.unit,
            "currency": item.currency,
            "calendar_id": item.calendar_id,
            "calendar_version": item.calendar_version,
            "note": item.note,
            "is_driving": item.is_driving,
            "units_per_time": item.units_per_time,
            "units_per_time_period": item.units_per_time_period,
            "hours_per_units_time_period": item.hours_per_units_time_period,
        },
    }


def _period_dto(item: P6ResourceAssignmentPeriodValue) -> dict[str, Any]:
    return {
        "contract_version": P6_RESOURCE_WRITE_API_VERSION,
        "kind": "resource_assignment_period",
        "scope": _scope_dto(item.scope),
        "period": {
            "assignment_id": item.assignment_id,
            "activity_id": item.activity_id,
            "resource_id": item.resource_id,
            "period_start": item.period_start,
            "units": item.units,
            "cost": item.cost,
        },
    }


__all__ = ["P6_RESOURCE_WRITE_API_VERSION", "P6ResourceWriteAPI"]
