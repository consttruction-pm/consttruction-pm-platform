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
from .p6_code_repository import (
    P6CodeApplicationService,
    P6CodeDefinition,
)
from .p6_code_assignment_repository import (
    P6CodeAssignment,
    P6CodeAssignmentApplicationService,
)

P6_CODE_API_VERSION = "p6-code-api.v1"
P6_CODE_ASSIGNMENT_API_VERSION = "p6-code-assignment-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_permission(
    policy: AuthorizationPolicy,
    auth_context: AuthorizationContext,
    permission: Permission,
) -> None:
    if not policy.is_allowed(auth_context, permission):
        raise AuthorizationError(f"authorization denied for permission={permission.value}")


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _code_dto(definition: P6CodeDefinition) -> dict[str, Any]:
    return {
        "contract_version": P6_CODE_API_VERSION,
        "kind": "p6_code",
        "scope": _scope_dto(definition.scope),
        "code": {
            "code_id": definition.code_id,
            "name": definition.name,
            "subject_area": definition.subject_area,
            "scope_kind": definition.scope_kind,
            "scope_key": definition.scope_key,
            "values": [
                {
                    "value_id": item.value_id,
                    "value": item.value,
                    "description": item.description,
                }
                for item in definition.values
            ],
        },
    }


def _assignment_dto(assignment: P6CodeAssignment) -> dict[str, Any]:
    return {
        "contract_version": P6_CODE_ASSIGNMENT_API_VERSION,
        "kind": "p6_code_assignment",
        "scope": _scope_dto(assignment.scope),
        "assignment": {
            "code_id": assignment.code_id,
            "value_id": assignment.value_id,
            "owner_type": assignment.owner_type,
            "owner_id": assignment.owner_id,
            "metadata": assignment.metadata,
        },
    }


@dataclass(frozen=True)
class P6CodeAPI:
    """Typed authorization/application boundary for persisted P6 code definitions."""

    service: P6CodeApplicationService
    authorization_policy: AuthorizationPolicy

    def create(
        self,
        definition: P6CodeDefinition,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(definition.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        return _code_dto(self.service.save(definition))

    def get(
        self,
        scope: BackendScope,
        code_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        result = self.service.read(scope, code_id)
        return None if result is None else _code_dto(result)

    def list(
        self,
        scope: BackendScope,
        *,
        subject_area: str | None = None,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        return tuple(
            _code_dto(item)
            for item in self.service.list(scope, subject_area=subject_area)
        )


@dataclass(frozen=True)
class P6CodeAssignmentAPI:
    """Typed authorization/application boundary for persisted P6 code assignments."""

    service: P6CodeAssignmentApplicationService
    authorization_policy: AuthorizationPolicy

    def create(
        self,
        assignment: P6CodeAssignment,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(assignment.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        return _assignment_dto(self.service.save(assignment))

    def get(
        self,
        scope: BackendScope,
        code_id: str,
        value_id: str,
        owner_type: str,
        owner_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        result = self.service.read(scope, code_id, value_id, owner_type, owner_id)
        return None if result is None else _assignment_dto(result)

    def list(
        self,
        scope: BackendScope,
        *,
        owner_type: str | None = None,
        owner_id: str | None = None,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        return tuple(
            _assignment_dto(item)
            for item in self.service.list(scope, owner_type=owner_type, owner_id=owner_id)
        )


__all__ = [
    "P6_CODE_API_VERSION",
    "P6_CODE_ASSIGNMENT_API_VERSION",
    "P6CodeAPI",
    "P6CodeAssignmentAPI",
]
