from __future__ import annotations

"""Authenticated API for versioned per-relationship schedule lag calendars."""

from dataclasses import dataclass
from typing import Any, Protocol

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .calendar_master_repository import (
    CalendarMasterRepository,
    CalendarPersistenceError,
    RelationshipLagCalendarAssignmentMaster,
)


P6_RELATIONSHIP_LAG_CALENDAR_API_VERSION = "p6-relationship-lag-calendar.v1"


class RelationshipLagCalendarAssignmentRepository(Protocol):
    def get_relationship_lag(
        self, scope: BackendScope, relationship_id: str
    ) -> RelationshipLagCalendarAssignmentMaster | None: ...

    def save_relationship_lag(
        self,
        assignment: RelationshipLagCalendarAssignmentMaster,
        expected_revision: int | None = None,
    ) -> RelationshipLagCalendarAssignmentMaster: ...


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if (
        scope.tenant_id != auth_context.tenant_id
        or scope.project_id != auth_context.project_id
    ):
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _dto(assignment: RelationshipLagCalendarAssignmentMaster) -> dict[str, Any]:
    return {
        "contract_version": P6_RELATIONSHIP_LAG_CALENDAR_API_VERSION,
        "kind": "p6_relationship_lag_calendar_assignment",
        "scope": {
            "tenant_id": assignment.scope.tenant_id,
            "project_id": assignment.scope.project_id,
            "project_revision": assignment.scope.project_revision,
        },
        "assignment": {
            "relationship_id": assignment.relationship_id,
            "option": assignment.option.value,
            "calendar_id": assignment.calendar_id,
            "calendar_version": assignment.calendar_version,
            "record_revision": assignment.record_revision,
        },
    }


@dataclass(frozen=True)
class P6RelationshipLagCalendarAPI:
    """Permission-checked read/write API for per-relationship lag-calendar inputs."""

    repository: RelationshipLagCalendarAssignmentRepository
    authorization_policy: AuthorizationPolicy
    calendar_repository: CalendarMasterRepository | None = None

    def get(
        self,
        scope: BackendScope,
        relationship_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("RELATIONSHIP_LAG_CALENDAR_READ_NOT_AUTHORIZED")
        result = self.repository.get_relationship_lag(scope, relationship_id)
        return None if result is None else _dto(result)

    def save(
        self,
        assignment: RelationshipLagCalendarAssignmentMaster,
        *,
        auth_context: AuthorizationContext,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        _require_scope(assignment.scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
            raise AuthorizationError("RELATIONSHIP_LAG_CALENDAR_WRITE_NOT_AUTHORIZED")
        if not isinstance(assignment, RelationshipLagCalendarAssignmentMaster):
            raise CalendarPersistenceError("INVALID_RELATIONSHIP_LAG_ASSIGNMENT")
        assignment.validate()
        if assignment.calendar_id is not None:
            if self.calendar_repository is None:
                raise CalendarPersistenceError("CALENDAR_REPOSITORY_UNAVAILABLE")
            calendar = self.calendar_repository.get(
                assignment.scope,
                assignment.calendar_id,
                assignment.calendar_version or "",
            )
            if calendar is None:
                raise CalendarPersistenceError("CALENDAR_NOT_FOUND")
        stored = self.repository.save_relationship_lag(
            assignment, expected_revision=expected_revision
        )
        return _dto(stored)


__all__ = [
    "P6_RELATIONSHIP_LAG_CALENDAR_API_VERSION",
    "P6RelationshipLagCalendarAPI",
    "RelationshipLagCalendarAssignmentRepository",
]
