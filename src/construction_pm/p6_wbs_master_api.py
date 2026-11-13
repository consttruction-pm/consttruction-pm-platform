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
from .wbs_master_repository import (
    PercentCompleteTechnique,
    WBSMaster,
    WBSMasterRepository,
    WBSMilestone,
    weighted_percent_complete,
)


P6_WBS_MASTER_API_VERSION = "p6-wbs-master-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _milestone_dto(item: WBSMilestone) -> dict[str, Any]:
    return {
        "milestone_id": item.milestone_id,
        "name": item.name,
        "weight": float(item.weight),
        "completed": item.completed,
        "sequence_number": item.sequence_number,
        "record_revision": item.record_revision,
    }


def _dto(
    item: WBSMaster, milestones: tuple[WBSMilestone, ...] | None = None
) -> dict[str, Any]:
    loaded = milestones or ()
    percent = (
        weighted_percent_complete(loaded)
        if item.percent_complete_technique is PercentCompleteTechnique.MILESTONES
        else None
    )
    return {
        "contract_version": P6_WBS_MASTER_API_VERSION,
        "kind": "p6_wbs_master",
        "scope": _scope_dto(item.scope),
        "wbs": {
            "wbs_id": item.wbs_id,
            "parent_kind": item.parent_kind.value,
            "parent_wbs_id": item.parent_wbs_id,
            "code": item.code,
            "name": item.name,
            "sequence_number": item.sequence_number,
            "record_revision": item.record_revision,
            "status": item.status.value,
            "percent_complete_technique": item.percent_complete_technique.value,
            "percent_complete": percent,
        },
        "milestones": [_milestone_dto(entry) for entry in loaded],
    }


@dataclass(frozen=True)
class P6WBSMasterAPI:
    """Authenticated application boundary for canonical WBS master data."""

    repository: WBSMasterRepository
    authorization_policy: AuthorizationPolicy

    def create(self, item: WBSMaster, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        _require_scope(item.scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
            raise AuthorizationError("authorization denied for permission=project.write")
        return _dto(self.repository.save(item, expected_revision=0))

    def update(
        self,
        item: WBSMaster,
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(item.scope, auth_context)
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 1
        ):
            raise ValueError("EXPECTED_REVISION_REQUIRED")
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
            raise AuthorizationError("authorization denied for permission=project.write")
        stored = self.repository.save(item, expected_revision=expected_revision)
        return _dto(stored, self.repository.list_milestones(item.scope, stored.wbs_id))

    def delete(
        self,
        scope: BackendScope,
        wbs_id: str,
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        """Delete an unused WBS node only for a current, authorized revision."""
        _require_scope(scope, auth_context)
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 1
        ):
            raise ValueError("EXPECTED_REVISION_REQUIRED")
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
            raise AuthorizationError("authorization denied for permission=project.write")
        self.repository.delete(scope, wbs_id, expected_revision=expected_revision)
        return {
            "contract_version": P6_WBS_MASTER_API_VERSION,
            "kind": "p6_wbs_master_delete",
            "scope": _scope_dto(scope),
            "wbs_id": wbs_id,
            "deleted": True,
        }

    def get(
        self,
        scope: BackendScope,
        wbs_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("authorization denied for permission=project.read")
        item = self.repository.get(scope, wbs_id)
        if item is None:
            return None
        return _dto(item, self.repository.list_milestones(scope, wbs_id))

    def list(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("authorization denied for permission=project.read")
        return tuple(
            _dto(item, self.repository.list_milestones(scope, item.wbs_id))
            for item in self.repository.list(scope)
        )

    def replace_milestones(
        self,
        scope: BackendScope,
        wbs_id: str,
        milestones: tuple[WBSMilestone, ...],
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 1
        ):
            raise ValueError("EXPECTED_REVISION_REQUIRED")
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
            raise AuthorizationError("authorization denied for permission=project.write")
        item, stored = self.repository.replace_milestones(
            scope, wbs_id, milestones, expected_revision=expected_revision
        )
        return _dto(item, stored)


__all__ = ["P6_WBS_MASTER_API_VERSION", "P6WBSMasterAPI"]
