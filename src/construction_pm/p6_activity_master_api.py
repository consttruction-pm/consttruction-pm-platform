from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .activity_master_repository import (
    ActivityMaster,
    ActivityMasterRepository,
    ActivityPersistenceError,
)
from .backend_p0.models import BackendScope
from .scheduling.activity import (
    ActivityLevelingPriority,
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
    PercentCompleteType,
)
from .scheduling.time_duration import DurationUnit


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
            "activity_type": item.activity_type.value,
            "status": item.status.value,
            "status_code": item.status_code.value,
            "duration_value": str(item.duration_value),
            "duration_unit": item.duration_unit.value,
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
            "record_revision": item.record_revision,
        },
    }


@dataclass(frozen=True)
class P6ActivityMasterAPI:
    """Authenticated application boundary over authoritative Activity Master persistence."""

    repository: ActivityMasterRepository
    authorization_policy: AuthorizationPolicy

    def create(
        self,
        activity: ActivityMaster,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(activity.scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
            raise AuthorizationError("authorization denied for permission=project.write")
        return _dto(self.repository.save(activity, expected_revision=0))

    def update(
        self,
        activity: ActivityMaster,
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(activity.scope, auth_context)
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise ValueError("EXPECTED_REVISION_REQUIRED")
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
            raise AuthorizationError("authorization denied for permission=project.write")
        return _dto(self.repository.save(activity, expected_revision=expected_revision))

    def update_fields(
        self,
        scope: BackendScope,
        activity_id: str,
        *,
        expected_revision: int,
        changes: Mapping[str, object],
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        """Apply an explicit, field-limited edit with record-revision locking.

        Only the fields accepted here can change. Actual dates, progress, status
        codes, and every other persisted field stay owned by their dedicated
        workflows and are never taken directly from an AI payload.
        """
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
            raise AuthorizationError("authorization denied for permission=project.write")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise ValueError("EXPECTED_REVISION_REQUIRED")
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise ValueError("INVALID_ACTIVITY_ID")
        if not isinstance(changes, Mapping) or not changes:
            raise ValueError("ACTIVITY_UPDATE_CHANGES_REQUIRED")
        if set(changes) - {"name", "duration_value", "duration_unit"}:
            raise ValueError("UNSUPPORTED_ACTIVITY_UPDATE_FIELD")
        existing = self.repository.get(scope, activity_id)
        if existing is None:
            raise ActivityPersistenceError("ACTIVITY_NOT_FOUND")
        if existing.record_revision != expected_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")

        updates: dict[str, object] = {}
        if "name" in changes:
            name = changes["name"]
            if not isinstance(name, str) or not name.strip():
                raise ValueError("INVALID_ACTIVITY_NAME")
            updates["name"] = name.strip()
        duration_fields = {"duration_value", "duration_unit"} & set(changes)
        if duration_fields:
            if duration_fields != {"duration_value", "duration_unit"}:
                raise ValueError("DURATION_UPDATE_PAIR_REQUIRED")
            raw_duration = changes["duration_value"]
            if isinstance(raw_duration, bool):
                raise ValueError("INVALID_DURATION_VALUE")
            try:
                duration = Decimal(str(raw_duration))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise ValueError("INVALID_DURATION_VALUE") from exc
            if not duration.is_finite() or duration < 0:
                raise ValueError("INVALID_DURATION_VALUE")
            updates["duration_value"] = duration
            updates["duration_unit"] = DurationUnit(str(changes["duration_unit"]))

        updated = replace(existing, **updates)
        updated.validate()
        return _dto(self.repository.save(updated, expected_revision=expected_revision))

    def get(
        self,
        scope: BackendScope,
        activity_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("authorization denied for permission=project.read")
        item = self.repository.get(scope, activity_id)
        return None if item is None else _dto(item)

    def list(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("authorization denied for permission=project.read")
        return tuple(_dto(item) for item in self.repository.list(scope))


__all__ = ["P6_ACTIVITY_MASTER_API_VERSION", "P6ActivityMasterAPI"]
