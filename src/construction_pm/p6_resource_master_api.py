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
from .calendar_master_repository import CalendarMasterRepository
from .p6_resource_master_repository import (
    P6Resource,
    P6ResourceRepository,
    resource_tree_order,
)

P6_RESOURCE_API_VERSION = "p6-resource-api.v1"


def _require_scope(
    tenant_id: str, project_id: str, auth: AuthorizationContext
) -> None:
    auth.validate()
    if tenant_id != auth.tenant_id or project_id != auth.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _permission(
    policy: AuthorizationPolicy, auth: AuthorizationContext, permission: Permission
) -> None:
    if not policy.is_allowed(auth, permission):
        raise AuthorizationError(
            f"authorization denied for permission={permission.value}"
        )


def _dto(resource: P6Resource) -> dict[str, Any]:
    return {
        "contract_version": P6_RESOURCE_API_VERSION,
        "kind": "p6_resource",
        "scope": {
            "tenant_id": resource.tenant_id,
            "project_id": resource.project_id,
            "project_revision": resource.project_revision,
        },
        "resource": {
            "resource_id": resource.resource_id,
            "name": resource.name,
            "resource_type": resource.resource_type,
            "parent_resource_id": resource.parent_resource_id,
            "calendar_id": resource.calendar_id,
            "default_units_per_time": resource.default_units_per_time,
            "unit_of_measure": resource.unit_of_measure,
            "email": resource.email,
            "is_active": resource.is_active,
            "record_revision": resource.record_revision,
        },
    }


@dataclass(frozen=True)
class P6ResourceAPI:
    """Read/write boundary over the authoritative resource master.

    Resource calendar assignment is enforced here, not only in the editor: a
    stored ``calendar_id`` must name a calendar that exists in the same
    tenant/project/revision scope. The resource master stores only the calendar
    identity; version binding stays with the persisted calendar and assignment
    facts that already carry it.
    """

    repository: P6ResourceRepository
    authorization_policy: AuthorizationPolicy
    calendar_repository: CalendarMasterRepository

    @staticmethod
    def _resource_ancestry(
        resource_id: str, parent_resource_id: str | None, items: tuple[P6Resource, ...]
    ) -> tuple[str, ...]:
        """Resolve self-to-root ancestry from the tenant/project-scoped master."""
        by_id = {item.resource_id: item for item in items}
        ancestry = [resource_id]
        seen = {resource_id}
        cursor = parent_resource_id
        while cursor is not None:
            if cursor in seen or cursor not in by_id:
                raise ValueError("RESOURCE_HIERARCHY_INVALID")
            seen.add(cursor)
            ancestry.append(cursor)
            cursor = by_id[cursor].parent_resource_id
        return tuple(ancestry)

    def _resource_access_allowed(
        self, auth_context: AuthorizationContext, resource_id: str,
        parent_resource_id: str | None, items: tuple[P6Resource, ...],
    ) -> bool:
        # Legacy/non-P6 policy adapters retain their established behavior. The
        # persisted P6 global policy exposes this method and is always enforced.
        checker = getattr(self.authorization_policy, "can_access_resource", None)
        if not callable(checker):
            return True
        ancestry = self._resource_ancestry(resource_id, parent_resource_id, items)
        return bool(checker(auth_context, resource_id, ancestry))

    def _validate_calendar(self, resource: P6Resource) -> None:
        if resource.calendar_id is None:
            # No explicit calendar: the project calendar resolves capacity at
            # scheduling time. This is a defined default, not a silent bypass.
            return
        scope = BackendScope(
            resource.tenant_id, resource.project_id, resource.project_revision
        )
        calendars = self.calendar_repository.list(scope)
        if not any(
            calendar.calendar_id == resource.calendar_id for calendar in calendars
        ):
            raise ValueError("RESOURCE_CALENDAR_NOT_FOUND")

    def _validate_parent(self, resource: P6Resource) -> None:
        if resource.parent_resource_id is None:
            return
        items = self.repository.list(
            resource.tenant_id, resource.project_id, resource.project_revision
        )
        by_id = {item.resource_id: item for item in items}
        if resource.parent_resource_id not in by_id:
            raise ValueError("RESOURCE_PARENT_NOT_FOUND")
        seen = {resource.resource_id}
        cursor = resource.parent_resource_id
        while cursor is not None:
            if cursor in seen:
                raise ValueError("RESOURCE_HIERARCHY_CYCLE")
            seen.add(cursor)
            cursor = by_id[cursor].parent_resource_id if cursor in by_id else None

    def create(self, resource: P6Resource, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        _require_scope(resource.tenant_id, resource.project_id, auth_context)
        _permission(
            self.authorization_policy, auth_context, Permission.PROJECT_WRITE
        )
        resource.validate()
        existing = self.repository.get(
            resource.tenant_id,
            resource.project_id,
            resource.project_revision,
            resource.resource_id,
        )
        if existing is not None:
            # Create must never silently overwrite a stored master. The editor
            # uses PATCH with the expected revision for every change.
            raise ValueError("RESOURCE_ALREADY_EXISTS")
        self._validate_calendar(resource)
        self._validate_parent(resource)
        items = self.repository.list(
            resource.tenant_id, resource.project_id, resource.project_revision
        )
        if not self._resource_access_allowed(
            auth_context, resource.resource_id, resource.parent_resource_id, items
        ):
            raise AuthorizationError("RESOURCE_ACCESS_DENIED")
        return _dto(self.repository.save(resource))

    def update(
        self,
        resource: P6Resource,
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(resource.tenant_id, resource.project_id, auth_context)
        _permission(
            self.authorization_policy, auth_context, Permission.PROJECT_WRITE
        )
        if expected_revision < 1:
            raise ValueError("RESOURCE_REVISION_REQUIRED")
        resource.validate()
        current = self.repository.get(
            resource.tenant_id, resource.project_id, resource.project_revision,
            resource.resource_id,
        )
        if current is None:
            raise ValueError("RESOURCE_NOT_FOUND")
        self._validate_calendar(resource)
        self._validate_parent(resource)
        items = self.repository.list(
            resource.tenant_id, resource.project_id, resource.project_revision
        )
        if not self._resource_access_allowed(
            auth_context, current.resource_id, current.parent_resource_id, items
        ) or not self._resource_access_allowed(
            auth_context, resource.resource_id, resource.parent_resource_id, items
        ):
            raise AuthorizationError("RESOURCE_ACCESS_DENIED")
        return _dto(
            self.repository.save(resource, expected_revision=expected_revision)
        )

    def get(
        self,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        resource_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(tenant_id, project_id, auth_context)
        _permission(
            self.authorization_policy, auth_context, Permission.PROJECT_READ
        )
        item = self.repository.get(
            tenant_id, project_id, project_revision, resource_id
        )
        if item is None:
            return None
        items = self.repository.list(tenant_id, project_id, project_revision)
        if not self._resource_access_allowed(
            auth_context, item.resource_id, item.parent_resource_id, items
        ):
            return None
        return _dto(item)

    def list(
        self,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(tenant_id, project_id, auth_context)
        _permission(
            self.authorization_policy, auth_context, Permission.PROJECT_READ
        )
        items = self.repository.list(tenant_id, project_id, project_revision)
        visible = tuple(
            item for item in items
            if self._resource_access_allowed(
                auth_context, item.resource_id, item.parent_resource_id, items
            )
        )
        return tuple(_dto(item) for item in resource_tree_order(visible))


__all__ = ["P6_RESOURCE_API_VERSION", "P6ResourceAPI"]
