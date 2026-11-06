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
    # Form Builder capabilities are separate grants, not aliases of project write.
    FORM_READ = "form.read"
    FORM_CREATE = "form.create"
    FORM_DESIGN = "form.design"
    FORM_FILL = "form.fill"
    FORM_SUBMIT = "form.submit"
    FORM_REVIEW = "form.review"
    FORM_APPROVE = "form.approve"
    FORM_PUBLISH = "form.publish"
    FORM_EXPORT = "form.export"
    FORM_LIBRARY_ADMIN = "form.library.admin"
    # Learning grants are deliberately absent from default role mappings:
    # deployments must explicitly grant each scope/action instead of inheriting
    # project read/write or admin access implicitly.
    AI_LEARNING_USER_READ = "ai_learning.user.read"
    AI_LEARNING_USER_WRITE = "ai_learning.user.write"
    AI_LEARNING_PROJECT_READ = "ai_learning.project.read"
    AI_LEARNING_PROJECT_WRITE = "ai_learning.project.write"
    AI_LEARNING_TENANT_READ = "ai_learning.tenant.read"
    AI_LEARNING_TENANT_WRITE = "ai_learning.tenant.write"
    AI_LEARNING_GENERAL_READ = "ai_learning.general.read"
    AI_LEARNING_GENERAL_CANDIDATE_CREATE = "ai_learning.general.candidate.create"
    AI_LEARNING_GENERAL_VALIDATE = "ai_learning.general.validate"
    AI_LEARNING_GENERAL_PUBLISH = "ai_learning.general.publish"
    AI_LEARNING_GENERAL_RETIRE = "ai_learning.general.retire"


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

    def permissions_for_role(self, role: str) -> FrozenSet[Permission]:
        """Return a read-only role grant set for explicit environment composition."""
        if not isinstance(role, str) or not role.strip():
            raise AuthorizationError("INVALID_AUTHORIZATION_ROLE")
        return self._role_permissions.get(role, frozenset())

    def is_allowed(self, context: AuthorizationContext, permission: Permission) -> bool:
        context.validate()
        return any(
            permission in self.permissions_for_role(role)
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
            "viewer": frozenset({Permission.PROJECT_READ, Permission.FORM_READ}),
            "planner": frozenset(
                {
                    Permission.PROJECT_READ,
                    Permission.PROJECT_WRITE,
                    Permission.PROJECT_SCHEDULE,
                    Permission.FORM_READ,
                    Permission.FORM_CREATE,
                    Permission.FORM_DESIGN,
                    Permission.FORM_FILL,
                    Permission.FORM_SUBMIT,
                    Permission.FORM_REVIEW,
                    Permission.FORM_EXPORT,
                }
            ),
            "project_admin": frozenset(
                {
                    Permission.PROJECT_READ,
                    Permission.PROJECT_WRITE,
                    Permission.PROJECT_SCHEDULE,
                    Permission.PROJECT_ADMIN,
                    Permission.FORM_READ,
                    Permission.FORM_CREATE,
                    Permission.FORM_DESIGN,
                    Permission.FORM_FILL,
                    Permission.FORM_SUBMIT,
                    Permission.FORM_REVIEW,
                    Permission.FORM_APPROVE,
                    Permission.FORM_PUBLISH,
                    Permission.FORM_EXPORT,
                    Permission.FORM_LIBRARY_ADMIN,
                }
            ),
        }
    )
