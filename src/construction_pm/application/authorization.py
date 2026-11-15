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
    # P6 V26 project-security capabilities used at operation boundaries.
    ACTIVITY_VIEW = "activity.view"
    ACTIVITY_ADD_EDIT = "activity.add_edit"
    ACTIVITY_EDIT = "activity.edit"
    ACTIVITY_DELETE = "activity.delete"
    ACTIVITY_RELATIONSHIP_MANAGE = "activity.relationship.add_edit_delete"
    ISSUE_VIEW = "issue.view"
    ISSUE_ADD_EDIT = "issue.add_edit"
    ISSUE_EDIT = "issue.edit"
    ISSUE_DELETE = "issue.delete"
    EXPENSE_VIEW = "expense.view"
    EXPENSE_ADD_EDIT = "expense.add_edit"
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
    # Knowledge base and assistant capabilities are separate grants. Reading
    # approved knowledge is not permission to contribute, review or publish it,
    # and assistant action approval is never implied by project write access.
    KNOWLEDGE_READ = "knowledge.read"
    KNOWLEDGE_CONTRIBUTE = "knowledge.contribute"
    KNOWLEDGE_REVIEW = "knowledge.review"
    KNOWLEDGE_PUBLISH = "knowledge.publish"
    ASSISTANT_ACTION = "assistant.action"


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
        # Application roles remain coarse organizational guardrails. The
        # EnterpriseProjectAuthorizationPolicy separately requires the exact
        # granular P6 project-profile grant (or an explicit legacy grant).
        role_grants = frozenset().union(*(
            self._role_permissions.get(role, frozenset()) for role in context.roles
        ))
        if permission in role_grants:
            return True
        legacy_guardrail = {
            Permission.ACTIVITY_VIEW: Permission.PROJECT_READ,
            Permission.ACTIVITY_ADD_EDIT: Permission.PROJECT_WRITE,
            Permission.ACTIVITY_EDIT: Permission.PROJECT_WRITE,
            Permission.ACTIVITY_DELETE: Permission.PROJECT_WRITE,
            Permission.ACTIVITY_RELATIONSHIP_MANAGE: Permission.PROJECT_WRITE,
            Permission.ISSUE_VIEW: Permission.PROJECT_READ,
            Permission.ISSUE_ADD_EDIT: Permission.PROJECT_WRITE,
            Permission.ISSUE_EDIT: Permission.PROJECT_WRITE,
            Permission.ISSUE_DELETE: Permission.PROJECT_WRITE,
            Permission.EXPENSE_VIEW: Permission.PROJECT_READ,
            Permission.EXPENSE_ADD_EDIT: Permission.PROJECT_WRITE,
        }.get(permission)
        return legacy_guardrail in role_grants if legacy_guardrail is not None else False

    def require(self, context: AuthorizationContext, permission: Permission) -> None:
        if not self.is_allowed(context, permission):
            raise AuthorizationError(
                f"authorization denied for permission={permission.value}"
            )


def default_role_permissions() -> dict[str, FrozenSet[Permission]]:
    """Return the authoritative role-to-permission grants of the default policy."""
    return {
        "viewer": frozenset(
            {
                Permission.PROJECT_READ,
                Permission.FORM_READ,
                Permission.KNOWLEDGE_READ,
            }
        ),
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
                Permission.KNOWLEDGE_READ,
                Permission.KNOWLEDGE_CONTRIBUTE,
                Permission.ASSISTANT_ACTION,
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
                Permission.KNOWLEDGE_READ,
                Permission.KNOWLEDGE_CONTRIBUTE,
                Permission.KNOWLEDGE_REVIEW,
                Permission.KNOWLEDGE_PUBLISH,
                Permission.ASSISTANT_ACTION,
            }
        ),
    }


def default_project_policy() -> RoleBasedAuthorizationPolicy:
    return RoleBasedAuthorizationPolicy(default_role_permissions())
