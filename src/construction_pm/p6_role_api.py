from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .p6_role_repository import P6Role, P6RoleRepository, role_tree_order

P6_ROLE_API_VERSION = "p6-role-api.v1"


def _scope(role: P6Role, auth: AuthorizationContext) -> None:
    auth.validate()
    if role.tenant_id != auth.tenant_id or role.project_id != auth.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _scope_values(tenant_id: str, project_id: str, project_revision: int, auth: AuthorizationContext) -> None:
    auth.validate()
    if tenant_id != auth.tenant_id or project_id != auth.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _permission(policy: AuthorizationPolicy, auth: AuthorizationContext, permission: Permission) -> None:
    if not policy.is_allowed(auth, permission):
        raise AuthorizationError(f"authorization denied for permission={permission.value}")


def _dto(role: P6Role) -> dict[str, Any]:
    return {
        "contract_version": P6_ROLE_API_VERSION,
        "kind": "p6_role",
        "scope": {
            "tenant_id": role.tenant_id,
            "project_id": role.project_id,
            "project_revision": role.project_revision,
        },
        "role": {
            "role_id": role.role_id,
            "name": role.name,
            "description": role.description,
            "parent_role_id": role.parent_role_id,
            "calculate_costs_from_units": role.calculate_costs_from_units,
            "record_revision": role.record_revision,
        },
    }


@dataclass(frozen=True)
class P6RoleAPI:
    repository: P6RoleRepository
    authorization_policy: AuthorizationPolicy

    def _validate_parent(self, role: P6Role) -> None:
        if role.parent_role_id is None:
            return
        items = self.repository.list(
            role.tenant_id, role.project_id, role.project_revision
        )
        by_id = {item.role_id: item for item in items}
        if role.parent_role_id not in by_id:
            raise ValueError("ROLE_PARENT_NOT_FOUND")
        seen = {role.role_id}
        cursor = role.parent_role_id
        while cursor is not None:
            if cursor in seen:
                raise ValueError("ROLE_HIERARCHY_CYCLE")
            seen.add(cursor)
            cursor = by_id[cursor].parent_role_id if cursor in by_id else None

    def create(self, role: P6Role, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        _scope(role, auth_context)
        _permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        role.validate()
        existing = self.repository.get(
            role.tenant_id, role.project_id, role.project_revision, role.role_id
        )
        if existing is not None:
            # Create must never silently overwrite a stored role. The editor
            # uses PATCH with the expected revision for every change.
            raise ValueError("ROLE_ALREADY_EXISTS")
        self._validate_parent(role)
        return _dto(self.repository.save(role))

    def update(self, role: P6Role, *, expected_revision: int, auth_context: AuthorizationContext) -> dict[str, Any]:
        _scope(role, auth_context)
        _permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        if expected_revision < 1:
            raise ValueError("ROLE_REVISION_REQUIRED")
        role.validate()
        self._validate_parent(role)
        return _dto(self.repository.save(role, expected_revision=expected_revision))

    def get(self, tenant_id: str, project_id: str, project_revision: int, role_id: str, *, auth_context: AuthorizationContext) -> dict[str, Any] | None:
        _scope_values(tenant_id, project_id, project_revision, auth_context)
        _permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        result = self.repository.get(tenant_id, project_id, project_revision, role_id)
        return None if result is None else _dto(result)

    def list(self, tenant_id: str, project_id: str, project_revision: int, *, auth_context: AuthorizationContext) -> tuple[dict[str, Any], ...]:
        _scope_values(tenant_id, project_id, project_revision, auth_context)
        _permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        items = self.repository.list(tenant_id, project_id, project_revision)
        return tuple(_dto(item) for item in role_tree_order(items))


__all__ = ["P6_ROLE_API_VERSION", "P6RoleAPI"]
