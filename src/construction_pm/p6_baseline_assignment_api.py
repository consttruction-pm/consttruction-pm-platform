from __future__ import annotations

"""Versioned API boundary for baseline summary-role assignment (BAS-001)."""

from dataclasses import dataclass
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_baseline_assignment import (
    P6BaselineAssignmentService,
    require_baseline_role,
)

P6_BASELINE_ASSIGNMENT_API_VERSION = "p6-baseline-assignment-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if (
        scope.tenant_id != auth_context.tenant_id
        or scope.project_id != auth_context.project_id
    ):
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_permission(
    policy: AuthorizationPolicy,
    auth_context: AuthorizationContext,
    permission: Permission,
) -> None:
    if not policy.is_allowed(auth_context, permission):
        raise AuthorizationError(
            f"authorization denied for permission={permission.value}"
        )


def _require_contract(contract_version: str) -> None:
    if contract_version != P6_BASELINE_ASSIGNMENT_API_VERSION:
        raise ValueError("BASELINE_ASSIGNMENT_CONTRACT_VERSION_UNSUPPORTED")


def _require_revision(scope: BackendScope, expected_revision: int) -> None:
    if (
        isinstance(expected_revision, bool)
        or not isinstance(expected_revision, int)
        or expected_revision < 0
    ):
        raise ValueError("BASELINE_ASSIGNMENT_REVISION_INVALID")
    if expected_revision != scope.project_revision:
        raise ValueError("BASELINE_ASSIGNMENT_STALE_REVISION")


def _scope_payload(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


@dataclass(frozen=True)
class P6BaselineAssignmentAPI:
    """Transport boundary over the authoritative role-assignment service."""

    service: P6BaselineAssignmentService
    authorization_policy: AuthorizationPolicy

    def assign(
        self,
        scope: BackendScope,
        role: str,
        baseline_id: str,
        *,
        expected_revision: int,
        replace: bool,
        auth_context: AuthorizationContext,
        contract_version: str = P6_BASELINE_ASSIGNMENT_API_VERSION,
    ) -> dict[str, Any]:
        _require_contract(contract_version)
        _require_scope(scope, auth_context)
        _require_permission(
            self.authorization_policy, auth_context, Permission.PROJECT_WRITE
        )
        _require_revision(scope, expected_revision)
        role = require_baseline_role(role)
        if not isinstance(baseline_id, str) or not baseline_id.strip():
            raise ValueError("INVALID_BASELINE_ID")
        if not isinstance(replace, bool):
            raise ValueError("INVALID_REPLACE_FLAG")
        assignment, replaced = self.service.assign(
            scope,
            role,
            baseline_id,
            assigned_by=auth_context.user_id,
            replace=replace,
        )
        return {
            "contract_version": P6_BASELINE_ASSIGNMENT_API_VERSION,
            "kind": "p6_baseline_role_assignment",
            "scope": _scope_payload(scope),
            "role": role,
            "assignment": assignment.to_payload(),
            "replaced": replaced,
        }

    def summary(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
        contract_version: str = P6_BASELINE_ASSIGNMENT_API_VERSION,
    ) -> dict[str, Any]:
        _require_contract(contract_version)
        _require_scope(scope, auth_context)
        _require_permission(
            self.authorization_policy, auth_context, Permission.PROJECT_READ
        )
        payload = self.service.summary(scope).to_payload()
        return {
            "contract_version": P6_BASELINE_ASSIGNMENT_API_VERSION,
            "kind": "p6_baseline_summary",
            **payload,
        }

    def history(
        self,
        scope: BackendScope,
        role: str,
        *,
        auth_context: AuthorizationContext,
        contract_version: str = P6_BASELINE_ASSIGNMENT_API_VERSION,
    ) -> dict[str, Any]:
        _require_contract(contract_version)
        _require_scope(scope, auth_context)
        _require_permission(
            self.authorization_policy, auth_context, Permission.PROJECT_READ
        )
        role = require_baseline_role(role)
        rows = self.service.history(scope, role)
        return {
            "contract_version": P6_BASELINE_ASSIGNMENT_API_VERSION,
            "kind": "p6_baseline_role_history",
            "scope": _scope_payload(scope),
            "role": role,
            "history": [row.to_payload() for row in rows],
        }


__all__ = [
    "P6_BASELINE_ASSIGNMENT_API_VERSION",
    "P6BaselineAssignmentAPI",
]
