from __future__ import annotations

"""Authenticated, versioned API boundary for persisted schedule constraints."""

from dataclasses import dataclass
from typing import Any

from construction_pm.activity_master_repository import ActivityMasterRepository
from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.constraint_master_repository import (
    ConstraintMaster,
    ConstraintMasterRepository,
)


P6_CONSTRAINT_API_VERSION = "p6-constraint-master-api.v1"


def _scope_dto(scope: BackendScope) -> dict[str, object]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _dto(item: ConstraintMaster) -> dict[str, Any]:
    return {
        "contract_version": P6_CONSTRAINT_API_VERSION,
        "kind": "p6_constraint_master",
        "scope": _scope_dto(item.scope),
        "constraint": {
            "constraint_id": item.constraint_id,
            "activity_id": item.activity_id,
            "constraint_type": item.constraint_type.value,
            "constraint_date": item.constraint_date.isoformat(),
            "record_revision": item.record_revision,
        },
    }


@dataclass(frozen=True)
class P6ConstraintAPI:
    """Shared Application/API boundary; it never evaluates constraint effects."""

    repository: ConstraintMasterRepository
    activity_repository: ActivityMasterRepository
    authorization_policy: AuthorizationPolicy

    def create(
        self,
        constraint: ConstraintMaster,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        self._authorize(constraint.scope, auth_context, Permission.PROJECT_WRITE)
        constraint.validate()
        self._require_activity(constraint.scope, constraint.activity_id)
        return _dto(self.repository.save(constraint, expected_revision=0))

    def update(
        self,
        constraint: ConstraintMaster,
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        self._authorize(constraint.scope, auth_context, Permission.PROJECT_WRITE)
        constraint.validate()
        self._require_activity(constraint.scope, constraint.activity_id)
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 1
        ):
            raise ValueError("EXPECTED_REVISION_REQUIRED")
        return _dto(self.repository.save(constraint, expected_revision=expected_revision))

    def get(
        self,
        scope: BackendScope,
        constraint_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        self._authorize(scope, auth_context, Permission.PROJECT_READ)
        item = self.repository.get(scope, constraint_id)
        return None if item is None else _dto(item)

    def list(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, ...], ...]:
        self._authorize(scope, auth_context, Permission.PROJECT_READ)
        return tuple(_dto(item) for item in self.repository.list(scope))

    def _require_activity(self, scope: BackendScope, activity_id: str) -> None:
        if self.activity_repository.get(scope, activity_id) is None:
            raise ValueError("CONSTRAINT_ACTIVITY_NOT_FOUND")

    def _authorize(
        self,
        scope: BackendScope,
        auth_context: AuthorizationContext,
        permission: Permission,
    ) -> None:
        scope.validate()
        if (
            auth_context.tenant_id != scope.tenant_id
            or auth_context.project_id != scope.project_id
        ):
            raise AuthorizationError("CROSS_SCOPE_ACCESS")
        if not self.authorization_policy.is_allowed(auth_context, permission):
            raise AuthorizationError(
                f"authorization denied for permission={permission.value}"
            )


__all__ = ["P6_CONSTRAINT_API_VERSION", "P6ConstraintAPI"]
