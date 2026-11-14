from __future__ import annotations

"""Authenticated application boundary over persisted schedule constraints.

Constraints are scheduling *inputs*: they are persisted here and the immutable
schedule snapshot composer reads them into the shared calculation core. This
boundary never calculates a date and never changes an activity row.
"""

from dataclasses import dataclass
from typing import Any

from .activity_master_repository import ActivityMasterRepository
from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .constraint_master_repository import (
    ConstraintMaster,
    ConstraintMasterRepository,
    ConstraintPersistenceError,
)
from .project_checkout import ProjectCheckoutLease, require_project_write_ownership
from .scheduling.activity import ActivityType


P6_CONSTRAINT_API_VERSION = "p6-constraint-api.v1"

_UNSUPPORTED_ACTIVITY_TYPES = frozenset(
    {ActivityType.LEVEL_OF_EFFORT, ActivityType.WBS_SUMMARY}
)


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


def _dto(constraint: ConstraintMaster) -> dict[str, Any]:
    return {
        "contract_version": P6_CONSTRAINT_API_VERSION,
        "kind": "p6_constraint",
        "scope": _scope_dto(constraint.scope),
        "constraint": {
            "constraint_id": constraint.constraint_id,
            "activity_id": constraint.activity_id,
            "constraint_type": constraint.constraint_type.value,
            "constraint_date": constraint.constraint_date.isoformat(),
            "record_revision": constraint.record_revision,
        },
    }


@dataclass(frozen=True)
class P6ConstraintAPI:
    """Permission-, lease- and scope-guarded constraint persistence."""

    repository: ConstraintMasterRepository
    authorization_policy: AuthorizationPolicy
    activity_repository: ActivityMasterRepository | None = None
    checkout_lease: ProjectCheckoutLease | None = None

    def create(
        self,
        constraint: ConstraintMaster,
        *,
        auth_context: AuthorizationContext,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        _require_scope(constraint.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        require_project_write_ownership(self.checkout_lease, constraint.scope, auth_context)
        self._validate_target(constraint)
        return _dto(self.repository.save(constraint, expected_revision=expected_revision))

    def update(
        self,
        constraint: ConstraintMaster,
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(constraint.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        require_project_write_ownership(self.checkout_lease, constraint.scope, auth_context)
        self._validate_target(constraint)
        return _dto(self.repository.save(constraint, expected_revision=expected_revision))

    def get(
        self,
        scope: BackendScope,
        constraint_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        result = self.repository.get(scope, constraint_id)
        return None if result is None else _dto(result)

    def list(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        return tuple(_dto(item) for item in self.repository.list(scope))

    def delete(
        self,
        scope: BackendScope,
        constraint_id: str,
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        require_project_write_ownership(self.checkout_lease, scope, auth_context)
        deleted = self.repository.delete(
            scope, constraint_id, expected_revision=expected_revision
        )
        return {
            "contract_version": P6_CONSTRAINT_API_VERSION,
            "kind": "p6_constraint_delete",
            "scope": _scope_dto(scope),
            "constraint_id": constraint_id,
            "deleted": deleted,
        }

    def _validate_target(self, constraint: ConstraintMaster) -> None:
        """Reject unknown activities, unsupported types and duplicate semantics.

        The shared scheduler still validates contradictory windows; this check
        only prevents storing a constraint that can never affect a schedule or
        that duplicates the same primary/secondary semantic twice.
        """
        constraint.validate()
        if self.activity_repository is not None:
            activity = self.activity_repository.get(constraint.scope, constraint.activity_id)
            if activity is None:
                raise ConstraintPersistenceError("ACTIVITY_NOT_FOUND_OR_SCOPE_MISMATCH")
            if activity.activity_type in _UNSUPPORTED_ACTIVITY_TYPES:
                raise ConstraintPersistenceError(
                    f"CONSTRAINT_ACTIVITY_TYPE_UNSUPPORTED:{activity.activity_type.value}"
                )
        for item in self.repository.list(constraint.scope):
            if item.constraint_id == constraint.constraint_id:
                continue
            if (
                item.activity_id == constraint.activity_id
                and item.constraint_type is constraint.constraint_type
            ):
                raise ConstraintPersistenceError("DUPLICATE_CONSTRAINT_TYPE")


__all__ = ["P6_CONSTRAINT_API_VERSION", "P6ConstraintAPI"]
