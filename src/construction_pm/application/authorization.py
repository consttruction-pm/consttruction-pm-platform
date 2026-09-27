from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Protocol


class AuthorizationError(PermissionError):
    """Raised when an application operation is not authorized."""


class Permission(str, Enum):
    PROJECT_READ = "project.read"
    PROJECT_WRITE = "project.write"
    PROJECT_SCHEDULE = "project.schedule"
    PROJECT_ADMIN = "project.admin"


@dataclass(frozen=True)
class AuthorizationContext:
    tenant_id: str
    project_id: str
    user_id: str
    roles: FrozenSet[str] = frozenset()

    def validate(self) -> None:
        for name, value in (("tenant_id", self.tenant_id), ("project_id", self.project_id), ("user_id", self.user_id)):
            if not isinstance(value, str) or not value.strip():
                raise AuthorizationError(f"INVALID_AUTHORIZATION_{name.upper()}")
        if not isinstance(self.roles, frozenset) or any(not isinstance(role, str) or not role.strip() for role in self.roles):
            raise AuthorizationError("INVALID_AUTHORIZATION_ROLES")


class AuthorizationPolicy(Protocol):
    def is_allowed(self, context: AuthorizationContext, permission: Permission) -> bool: ...


class RoleBasedAuthorizationPolicy:
    """Framework/provider-neutral role-to-permission policy."""

    def __init__(self, role_permissions: dict[str, FrozenSet[Permission]]) -> None:
        self._role_permissions = {
            role: frozenset(permissions)
            for role, permissions in role_permissions.items()
        }

    def is_allowed(self, context: AuthorizationContext, permission: Permission) -> bool:
        context.validate()
        return any(
            permission in self._role_permissions.get(role, frozenset())
            for role in context.roles
        )

    def require(self, context: AuthorizationContext, permission: Permission) -> None:
        if not self.is_allowed(context, permission):
            raise AuthorizationError(
                f"authorization denied for permission={permission.value}"
            )


def default_project_policy() -> RoleBasedAuthorizationPolicy:
    return RoleBasedAuthorizationPolicy(
        {
            "viewer": frozenset({Permission.PROJECT_READ}),
            "planner": frozenset(
                {Permission.PROJECT_READ, Permission.PROJECT_WRITE, Permission.PROJECT_SCHEDULE}
            ),
            "project_admin": frozenset(
                {
                    Permission.PROJECT_READ,
                    Permission.PROJECT_WRITE,
                    Permission.PROJECT_SCHEDULE,
                    Permission.PROJECT_ADMIN,
                }
            ),
        }
    )
