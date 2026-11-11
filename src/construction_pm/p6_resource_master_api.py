from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
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
    """Read/write boundary over the authoritative resource master."""

    repository: P6ResourceRepository
    authorization_policy: AuthorizationPolicy

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
        self._validate_parent(resource)
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
        self._validate_parent(resource)
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
        return None if item is None else _dto(item)

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
        return tuple(_dto(item) for item in resource_tree_order(items))


__all__ = ["P6_RESOURCE_API_VERSION", "P6ResourceAPI"]
