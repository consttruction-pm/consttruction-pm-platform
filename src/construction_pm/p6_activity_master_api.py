from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .activity_master_repository import ActivityMaster, ActivityMasterRepository
from .backend_p0.models import BackendScope
from .project_checkout import (
    ProjectCheckoutLease,
    require_project_write_ownership,
)
from .scheduling.activity import (
    ActivityDurationType,
    ActivityLevelingPriority,
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
    PercentCompleteType,
)


P6_ACTIVITY_MASTER_API_VERSION = "p6-activity-master-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _optional_iso(value: date | datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _dto(item: ActivityMaster) -> dict[str, Any]:
    return {
        "contract_version": P6_ACTIVITY_MASTER_API_VERSION,
        "kind": "p6_activity_master",
        "scope": _scope_dto(item.scope),
        "activity": {
            "activity_id": item.activity_id,
            "name": item.name,
            "short_name": item.short_name,
            "activity_type": item.activity_type.value,
            "status": item.status.value,
            "status_code": item.status_code.value,
            "duration_value": str(item.duration_value),
            "duration_unit": item.duration_unit.value,
            "duration_type": item.duration_type.value,
            "cost_account_id": item.cost_account_id,
            "actual_start": _optional_iso(item.actual_start),
            "actual_finish": _optional_iso(item.actual_finish),
            "remaining_duration": item.remaining_duration,
            "remaining_start": _optional_iso(item.remaining_start),
            "percent_complete": item.percent_complete,
            "percent_complete_type": item.percent_complete_type.value,
            "expected_finish": _optional_iso(item.expected_finish),
            "planned_finish": _optional_iso(item.planned_finish),
            "leveling_priority": item.leveling_priority.value,
            "original_duration": item.original_duration,
            "wbs_id": item.wbs_id,
            "record_revision": item.record_revision,
        },
    }


@dataclass(frozen=True)
class P6ActivityMasterAPI:
    """Authenticated application boundary over authoritative Activity Master persistence."""

    repository: ActivityMasterRepository
    authorization_policy: AuthorizationPolicy
    checkout_lease: ProjectCheckoutLease | None = None
    wbs_access_repository: Any | None = None

    def _require_wbs_permission(
        self,
        scope: BackendScope,
        auth_context: AuthorizationContext,
        wbs_id: str | None,
        permission: str,
    ) -> None:
        if wbs_id is None or self.wbs_access_repository is None:
            return
        checker = getattr(self.wbs_access_repository, "has_wbs_permission", None)
        if callable(checker) and not checker(scope, auth_context.user_id, wbs_id, permission):
            raise AuthorizationError("WBS_OBS_ACCESS_DENIED")

    def create(
        self,
        activity: ActivityMaster,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(activity.scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.ACTIVITY_ADD_EDIT):
            raise AuthorizationError("authorization denied for permission=activity.add_edit")
        require_project_write_ownership(self.checkout_lease, activity.scope, auth_context)
        self._require_wbs_permission(activity.scope, auth_context, activity.wbs_id, Permission.PROJECT_WRITE.value)
        return _dto(self.repository.save(activity, expected_revision=0))

    def update(
        self,
        activity: ActivityMaster,
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(activity.scope, auth_context)
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 1
        ):
            raise ValueError("EXPECTED_REVISION_REQUIRED")
        if not self.authorization_policy.is_allowed(auth_context, Permission.ACTIVITY_EDIT):
            raise AuthorizationError("authorization denied for permission=activity.edit")
        require_project_write_ownership(self.checkout_lease, activity.scope, auth_context)
        if self.wbs_access_repository is not None and not activity.wbs_id:
            raise AuthorizationError("ACTIVITY_WBS_REQUIRED")
        existing = self.repository.get(activity.scope, activity.activity_id)
        if existing is not None:
            self._require_wbs_permission(
                activity.scope, auth_context, existing.wbs_id, Permission.PROJECT_WRITE.value
            )
        self._require_wbs_permission(activity.scope, auth_context, activity.wbs_id, Permission.PROJECT_WRITE.value)
        return _dto(self.repository.save(activity, expected_revision=expected_revision))

    def get(
        self,
        scope: BackendScope,
        activity_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.ACTIVITY_VIEW):
            raise AuthorizationError("authorization denied for permission=activity.view")
        item = self.repository.get(scope, activity_id)
        if item is None:
            return None
        self._require_wbs_permission(scope, auth_context, item.wbs_id, Permission.PROJECT_READ.value)
        return _dto(item)

    def _can_read_activity(
        self, scope: BackendScope, auth_context: AuthorizationContext, wbs_id: str | None
    ) -> bool:
        if wbs_id is None or self.wbs_access_repository is None:
            return True
        checker = getattr(self.wbs_access_repository, "has_wbs_permission", None)
        return True if not callable(checker) else bool(
            checker(scope, auth_context.user_id, wbs_id, Permission.PROJECT_READ.value)
        )

    def list(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("authorization denied for permission=project.read")
        return tuple(
            _dto(item) for item in self.repository.list(scope)
            if self._can_read_activity(scope, auth_context, item.wbs_id)
        )


__all__ = ["P6_ACTIVITY_MASTER_API_VERSION", "P6ActivityMasterAPI"]
