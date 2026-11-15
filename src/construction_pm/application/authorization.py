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
    P6_UDF_ADMIN = "p6.udf.admin"
    P6_WBS_ADMIN = "p6.wbs.admin"
    P6_ACTIVITY_ADMIN = "p6.activity.admin"
    P6_ACTIVITY_RELATIONSHIP_ADMIN = "p6.activity.relationship.admin"
    P6_ACTIVITY_ID_ADMIN = "p6.activity.id.admin"
    P6_EXPENSE_ADMIN = "p6.expense.admin"
    P6_DISCUSSION_DELETE = "p6.discussion.delete"
    P6_ISSUE_ADMIN = "p6.issue.admin"
    P6_BASELINE_ADMIN = "p6.baseline.admin"
    P6_PROJECT_CALENDAR_ADMIN = "p6.project.calendar.admin"
    P6_RISK_ADMIN = "p6.risk.admin"
    P6_PROJECT_DOCUMENT_ADMIN = "p6.project.document.admin"
    P6_ASSIGN_PROJECT_BASELINE = "p6.project.baseline.assign"
    P6_APPLY_ACTUALS = "p6.actuals.apply"
    P6_STORE_PERIOD_PERFORMANCE = "p6.period.performance.store"
    P6_MONITOR_THRESHOLDS = "p6.thresholds.monitor"
    P6_COSTS_VIEW = "p6.costs.view"
    P6_RESOURCE_REQUEST_ADMIN = "p6.resource.request.admin"
    P6_PROJECT_CHECKOUT_ADMIN = "p6.project.checkout.admin"
    P6_LEVEL_RESOURCES = "p6.resources.level"
    P6_BASELINE_UPDATE = "p6.baseline.update"
    P6_GLOBAL_CHANGE = "p6.global.change"
    P6_EPS_ADMIN = "p6.eps.admin"
    P6_PROJECT_CREATE = "p6.project.create"
    P6_PROJECT_DELETE = "p6.project.delete"
    P6_EPS_COSTS_ADMIN = "p6.eps.costs.admin"
    P6_WBS_COSTS_ADMIN = "p6.wbs.costs.admin"
    P6_EXPORT_PROJECT_DATA = "p6.project.export"
    P6_PROJECT_LEVEL_LAYOUT_ADMIN = "p6.project.layout.admin"
    P6_REPORT_ADMIN = "p6.project.report.admin"
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
        p6_project_write_permissions = {
            Permission.P6_WBS_ADMIN, Permission.P6_ACTIVITY_ADMIN,
            Permission.P6_ACTIVITY_RELATIONSHIP_ADMIN, Permission.P6_ACTIVITY_ID_ADMIN,
            Permission.P6_EXPENSE_ADMIN, Permission.P6_DISCUSSION_DELETE,
            Permission.P6_ISSUE_ADMIN, Permission.P6_BASELINE_ADMIN,
            Permission.P6_PROJECT_CALENDAR_ADMIN, Permission.P6_RISK_ADMIN,
            Permission.P6_PROJECT_DOCUMENT_ADMIN, Permission.P6_ASSIGN_PROJECT_BASELINE,
            Permission.P6_APPLY_ACTUALS, Permission.P6_STORE_PERIOD_PERFORMANCE,
            Permission.P6_MONITOR_THRESHOLDS, Permission.P6_COSTS_VIEW,
            Permission.P6_RESOURCE_REQUEST_ADMIN, Permission.P6_PROJECT_CHECKOUT_ADMIN,
            Permission.P6_LEVEL_RESOURCES, Permission.P6_BASELINE_UPDATE,
            Permission.P6_GLOBAL_CHANGE, Permission.P6_EPS_ADMIN,
            Permission.P6_PROJECT_CREATE, Permission.P6_PROJECT_DELETE,
            Permission.P6_EPS_COSTS_ADMIN, Permission.P6_WBS_COSTS_ADMIN,
            Permission.P6_EXPORT_PROJECT_DATA, Permission.P6_PROJECT_LEVEL_LAYOUT_ADMIN,
            Permission.P6_REPORT_ADMIN,
        }
        return any(
            permission in self._role_permissions.get(role, frozenset())
            or (
                permission in p6_project_write_permissions
                and Permission.PROJECT_WRITE in self._role_permissions.get(role, frozenset())
            )
            for role in context.roles
        )

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
                Permission.P6_UDF_ADMIN,
                Permission.P6_ACTIVITY_ADMIN,
                Permission.P6_ACTIVITY_RELATIONSHIP_ADMIN,
                Permission.P6_ACTIVITY_ID_ADMIN,
                Permission.P6_EXPENSE_ADMIN,
                Permission.P6_DISCUSSION_DELETE,
                Permission.P6_ISSUE_ADMIN,
                Permission.P6_BASELINE_ADMIN,
                Permission.P6_PROJECT_CALENDAR_ADMIN,
                Permission.P6_RISK_ADMIN,
                Permission.P6_PROJECT_DOCUMENT_ADMIN,
                Permission.P6_ASSIGN_PROJECT_BASELINE,
                Permission.P6_APPLY_ACTUALS,
                Permission.P6_STORE_PERIOD_PERFORMANCE,
                Permission.P6_MONITOR_THRESHOLDS,
                Permission.P6_COSTS_VIEW,
                Permission.P6_RESOURCE_REQUEST_ADMIN,
                Permission.P6_PROJECT_CHECKOUT_ADMIN,
                Permission.P6_LEVEL_RESOURCES,
                Permission.P6_BASELINE_UPDATE,
                Permission.P6_GLOBAL_CHANGE,
                Permission.P6_EPS_ADMIN,
                Permission.P6_PROJECT_CREATE,
                Permission.P6_PROJECT_DELETE,
                Permission.P6_EPS_COSTS_ADMIN,
                Permission.P6_WBS_COSTS_ADMIN,
                Permission.P6_EXPORT_PROJECT_DATA,
                Permission.P6_PROJECT_LEVEL_LAYOUT_ADMIN,
                Permission.P6_REPORT_ADMIN,
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
                Permission.P6_UDF_ADMIN,
                Permission.P6_WBS_ADMIN,
                Permission.P6_ACTIVITY_ADMIN,
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
