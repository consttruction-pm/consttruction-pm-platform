from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .backend_p0.models import BackendScope
from .calendar_master_repository import CalendarMasterRepository, CalendarPersistenceError
from .calendar_snapshot_repository import CalendarSnapshotRepository

P6_CALENDAR_READ_API_VERSION = "p6-calendar-read-api.v1"


def _authorize(scope: BackendScope, auth_context: AuthorizationContext, policy: AuthorizationPolicy) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")
    if not policy.is_allowed(auth_context, Permission.PROJECT_READ):
        raise AuthorizationError("authorization denied for permission=project.read")


@dataclass(frozen=True)
class P6CalendarReadAPI:
    calendar_repository: CalendarMasterRepository
    snapshot_repository: CalendarSnapshotRepository
    authorization_policy: AuthorizationPolicy

    def list_calendars(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _authorize(scope, auth_context, self.authorization_policy)
        try:
            calendars = self.calendar_repository.list(scope)
        except CalendarPersistenceError:
            raise
        return {
            "contract_version": P6_CALENDAR_READ_API_VERSION,
            "kind": "calendar_catalog",
            "scope": _scope(scope),
            "calendars": [_calendar_dto(item) for item in calendars],
        }

    def get_snapshot(
        self,
        scope: BackendScope,
        calendar_id: str,
        calendar_version: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _authorize(scope, auth_context, self.authorization_policy)
        if not isinstance(calendar_id, str) or not calendar_id.strip():
            raise CalendarPersistenceError("INVALID_CALENDAR_REFERENCE")
        if not isinstance(calendar_version, str) or not calendar_version.strip():
            raise CalendarPersistenceError("INVALID_CALENDAR_REFERENCE")
        calendar = self.calendar_repository.get(scope, calendar_id, calendar_version)
        if calendar is None:
            return None
        snapshot = self.snapshot_repository.get(calendar)
        if snapshot is None:
            return None
        return {
            "contract_version": P6_CALENDAR_READ_API_VERSION,
            "kind": "calendar_snapshot",
            "scope": _scope(scope),
            "calendar": _calendar_dto(calendar),
            "snapshot": snapshot.snapshot,
        }


def _scope(scope: BackendScope) -> dict[str, object]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _calendar_dto(calendar: object) -> dict[str, object]:
    return {
        "calendar_id": calendar.calendar_id,
        "calendar_version": calendar.calendar_version,
        "kind": calendar.kind,
        "name": calendar.name,
        "record_revision": calendar.record_revision,
    }


__all__ = ["P6_CALENDAR_READ_API_VERSION", "P6CalendarReadAPI"]
