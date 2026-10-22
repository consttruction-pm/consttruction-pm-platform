from __future__ import annotations

"""Authenticated API boundary for publishing authoritative schedule snapshots."""

from dataclasses import dataclass
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .authoritative_schedule_input_composer import ScheduleInputDefinition
from .schedule_snapshot_publisher import (
    AuthoritativeScheduleSnapshotPublisher,
    ScheduleSnapshotPublicationError,
)


P6_SCHEDULE_SNAPSHOT_API_VERSION = "p6-schedule-snapshot-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


@dataclass(frozen=True)
class P6ScheduleSnapshotPublicationAPI:
    """Requires scheduling permission and publishes only from fresh persisted reads."""

    publisher: AuthoritativeScheduleSnapshotPublisher
    authorization_policy: AuthorizationPolicy

    def publish(
        self,
        scope: BackendScope,
        *,
        definition: ScheduleInputDefinition,
        timezone_name: str,
        auth_context: AuthorizationContext,
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_SCHEDULE):
            raise AuthorizationError("authorization denied for permission=project.schedule")
        try:
            result = self.publisher.publish(
                scope,
                definition=definition,
                timezone_name=timezone_name,
                actor_id=auth_context.user_id,
                request_id=request_id,
                idempotency_key=idempotency_key,
            )
        except ScheduleSnapshotPublicationError:
            raise
        return {
            "contract_version": P6_SCHEDULE_SNAPSHOT_API_VERSION,
            "kind": "schedule_input_snapshot",
            "scope": {
                "tenant_id": result.scope.tenant_id,
                "project_id": result.scope.project_id,
                "project_revision": result.scope.project_revision,
            },
            "snapshot_id": result.snapshot_id,
            "snapshot_hash": result.snapshot_hash,
            "calculation_identity": result.calculation_identity,
            "created_at": result.created_at.isoformat(),
        }


__all__ = [
    "P6_SCHEDULE_SNAPSHOT_API_VERSION",
    "P6ScheduleSnapshotPublicationAPI",
]
