from __future__ import annotations

"""Read the stored references that use one exact calendar version.

Usage is composed from the authoritative assignment, resource and resource
assignment repositories; it never guesses a calendar reference. A resource
master stores a calendar id without a version, so it is reported with
``calendar_version`` null and matched by id only.
"""

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
    ActivityCalendarAssignmentMaster,
    CalendarMasterRepository,
    CalendarPersistenceError,
    RelationshipLagCalendarAssignmentMaster,
)

P6_CALENDAR_USAGE_API_VERSION = "p6-calendar-usage-api.v1"


class _CalendarAssignmentSource(Protocol):
    def list_activities(self, scope: BackendScope) -> tuple[ActivityCalendarAssignmentMaster, ...]: ...
    def list_relationship_lag(self, scope: BackendScope) -> tuple[RelationshipLagCalendarAssignmentMaster, ...]: ...


class _ResourceSource(Protocol):
    def list(
        self, tenant_id: str, project_id: str, project_revision: int
    ) -> tuple[Any, ...]: ...


class _ResourceAssignmentSource(Protocol):
    def list(self, scope: BackendScope) -> tuple[Any, ...]: ...


@dataclass(frozen=True)
class P6CalendarUsageAPI:
    calendar_repository: CalendarMasterRepository
    assignment_repository: _CalendarAssignmentSource
    resource_repository: _ResourceSource
    resource_assignment_repository: _ResourceAssignmentSource
    authorization_policy: AuthorizationPolicy

    def list_usages(
        self,
        scope: BackendScope,
        calendar_id: str,
        calendar_version: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        scope.validate()
        auth_context.validate()
        if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
            raise AuthorizationError("CROSS_SCOPE_ACCESS")
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("authorization denied for permission=project.read")
        if not isinstance(calendar_id, str) or not calendar_id.strip():
            raise CalendarPersistenceError("INVALID_CALENDAR_REFERENCE")
        if not isinstance(calendar_version, str) or not calendar_version.strip():
            raise CalendarPersistenceError("INVALID_CALENDAR_REFERENCE")
        if self.calendar_repository.get(scope, calendar_id, calendar_version) is None:
            return None

        references: list[dict[str, Any]] = []
        for item in self.assignment_repository.list_activities(scope):
            if self._matches(item.calendar_id, item.calendar_version, calendar_id, calendar_version):
                references.append(
                    {
                        "kind": "activity_calendar_assignment",
                        "reference_id": item.activity_id,
                        "details": {"activity_id": item.activity_id, "record_revision": item.record_revision},
                    }
                )
        for lag in self.assignment_repository.list_relationship_lag(scope):
            if lag.calendar_id is None or lag.calendar_version is None:
                continue
            if self._matches(lag.calendar_id, lag.calendar_version, calendar_id, calendar_version):
                references.append(
                    {
                        "kind": "relationship_lag_calendar_assignment",
                        "reference_id": lag.relationship_id,
                        "details": {
                            "relationship_id": lag.relationship_id,
                            "option": lag.option.value,
                            "record_revision": lag.record_revision,
                        },
                    }
                )
        for resource in self.resource_repository.list(
            scope.tenant_id, scope.project_id, scope.project_revision
        ):
            calendar_reference = getattr(resource, "calendar_id", None)
            if calendar_reference == calendar_id:
                references.append(
                    {
                        "kind": "resource_calendar_assignment",
                        "reference_id": str(resource.resource_id),
                        "details": {
                            "resource_id": str(resource.resource_id),
                            "calendar_version": None,
                            "match": "calendar_id",
                        },
                    }
                )
        for assignment in self.resource_assignment_repository.list(scope):
            if assignment.calendar_id is None or assignment.calendar_version is None:
                continue
            if self._matches(
                assignment.calendar_id, assignment.calendar_version, calendar_id, calendar_version
            ):
                references.append(
                    {
                        "kind": "resource_assignment_calendar",
                        "reference_id": assignment.assignment_id,
                        "details": {
                            "assignment_id": assignment.assignment_id,
                            "activity_id": assignment.activity_id,
                            "resource_id": assignment.resource_id,
                        },
                    }
                )

        references.sort(key=lambda item: (item["kind"], item["reference_id"]))
        counts: dict[str, int] = {}
        for item in references:
            counts[item["kind"]] = counts.get(item["kind"], 0) + 1
        return {
            "contract_version": P6_CALENDAR_USAGE_API_VERSION,
            "kind": "calendar_usage",
            "scope": {
                "tenant_id": scope.tenant_id,
                "project_id": scope.project_id,
                "project_revision": scope.project_revision,
            },
            "calendar": {
                "calendar_id": calendar_id,
                "calendar_version": calendar_version,
            },
            "total": len(references),
            "counts": counts,
            "usages": references,
        }

    @staticmethod
    def _matches(
        stored_id: str,
        stored_version: str,
        calendar_id: str,
        calendar_version: str,
    ) -> bool:
        return stored_id == calendar_id and stored_version == calendar_version


__all__ = ["P6_CALENDAR_USAGE_API_VERSION", "P6CalendarUsageAPI"]
