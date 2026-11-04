from __future__ import annotations

from dataclasses import dataclass

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from construction_pm.backend_p0.models import BackendScope

from .quality_policy_pack import (
    ScheduleQualityPolicyPack,
    ScheduleQualityPolicyRepository,
)


SCHEDULE_QUALITY_POLICY_API_VERSION = "schedule-quality-policy-api.v1"


@dataclass(frozen=True)
class ScheduleQualityPolicyAPI:
    repository: ScheduleQualityPolicyRepository
    authorization_policy: AuthorizationPolicy
    transaction_manager: object

    def create(
        self,
        pack: ScheduleQualityPolicyPack,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, object]:
        self._authorize(pack.scope, auth_context, Permission.SCHEDULE_QUALITY_POLICY_ADMIN)
        if pack.created_by != auth_context.user_id:
            raise AuthorizationError("SCHEDULE_QUALITY_POLICY_CREATOR_MUST_BE_AUTHENTICATED_ACTOR")
        with self.transaction_manager.transaction():
            stored = self.repository.create(pack)
        return self._dto(stored)

    def approve(
        self,
        scope: BackendScope,
        policy_id: str,
        version: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, object]:
        self._authorize(scope, auth_context, Permission.SCHEDULE_QUALITY_POLICY_ADMIN)
        with self.transaction_manager.transaction():
            stored = self.repository.approve(
                scope,
                policy_id,
                version,
                approved_by=auth_context.user_id,
            )
        return self._dto(stored)

    def list(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, object]:
        self._authorize(scope, auth_context, Permission.PROJECT_READ)
        with self.transaction_manager.transaction():
            packs = self.repository.list(scope)
        return {
            "contract_version": SCHEDULE_QUALITY_POLICY_API_VERSION,
            "scope": {"tenant_id": scope.tenant_id, "project_id": scope.project_id},
            "policy_packs": [self._dto(item)["policy_pack"] for item in packs],
        }

    def latest_approved(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, object] | None:
        self._authorize(scope, auth_context, Permission.PROJECT_READ)
        with self.transaction_manager.transaction():
            pack = self.repository.latest_approved(scope)
        return None if pack is None else self._dto(pack)

    def _authorize(
        self,
        scope: BackendScope,
        auth_context: AuthorizationContext,
        permission: Permission,
    ) -> None:
        scope.validate()
        auth_context.validate()
        if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
            raise AuthorizationError("CROSS_SCOPE_ACCESS")
        if not self.authorization_policy.is_allowed(auth_context, permission):
            raise AuthorizationError(f"authorization denied for permission={permission.value}")

    @staticmethod
    def _dto(pack: ScheduleQualityPolicyPack) -> dict[str, object]:
        return {
            "contract_version": SCHEDULE_QUALITY_POLICY_API_VERSION,
            "policy_pack": {
                "tenant_id": pack.scope.tenant_id,
                "project_id": pack.scope.project_id,
                "project_revision": pack.scope.project_revision,
                "policy_id": pack.policy_id,
                "version": pack.version,
                "name": pack.name,
                "scoring_method": pack.scoring_method,
                "thresholds": dict(pack.thresholds),
                "weights": dict(pack.weights),
                "created_by": pack.created_by,
                "created_at": pack.created_at.isoformat(),
                "approved_by": pack.approved_by,
                "approved_at": None if pack.approved_at is None else pack.approved_at.isoformat(),
                "status": "approved" if pack.approved_at is not None else "draft",
            },
        }


__all__ = [
    "SCHEDULE_QUALITY_POLICY_API_VERSION",
    "ScheduleQualityPolicyAPI",
]
