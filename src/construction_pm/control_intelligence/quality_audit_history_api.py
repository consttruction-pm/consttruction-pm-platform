from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from construction_pm.backend_p0.models import BackendScope

from .quality_audit_history import ScheduleQualityAuditHistoryRepository


SCHEDULE_QUALITY_AUDIT_HISTORY_VERSION = "schedule-quality-audit-history.v1"


@dataclass(frozen=True)
class ScheduleQualityAuditHistoryAPI:
    repository: ScheduleQualityAuditHistoryRepository
    authorization_policy: AuthorizationPolicy

    def list_for_project(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
        limit: int = 100,
    ) -> dict[str, object]:
        self._authorize(scope, auth_context)
        records = self.repository.list_for_project(
            scope.tenant_id, scope.project_id, limit=limit
        )
        return {
            "contract_version": SCHEDULE_QUALITY_AUDIT_HISTORY_VERSION,
            "scope": {
                "tenant_id": scope.tenant_id,
                "project_id": scope.project_id,
            },
            "audits": [self._summary(record) for record in records],
        }

    def get(
        self,
        scope: BackendScope,
        audit_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, object] | None:
        self._authorize(scope, auth_context)
        record = self.repository.get(scope.tenant_id, scope.project_id, audit_id)
        if record is None:
            return None
        report = dict(record.report)
        report["audit_history"] = {
            "status": "persisted",
            "audit_id": record.audit_id,
            "created_at": record.created_at.isoformat(),
        }
        return {
            "contract_version": SCHEDULE_QUALITY_AUDIT_HISTORY_VERSION,
            "audit": {
                **self._summary(record),
                "report": report,
            },
        }

    def _authorize(
        self,
        scope: BackendScope,
        auth_context: AuthorizationContext,
    ) -> None:
        scope.validate()
        auth_context.validate()
        if (
            scope.tenant_id != auth_context.tenant_id
            or scope.project_id != auth_context.project_id
        ):
            raise AuthorizationError("CROSS_SCOPE_ACCESS")
        if not self.authorization_policy.is_allowed(
            auth_context, Permission.PROJECT_READ
        ):
            raise AuthorizationError("authorization denied for permission=project.read")

    @staticmethod
    def _summary(record) -> dict[str, object]:
        report: Mapping[str, object] = record.report
        summary = report.get("summary", {})
        quality_index = report.get("quality_index", {})
        return {
            "audit_id": record.audit_id,
            "query_id": record.query_id,
            "scope": {
                "tenant_id": record.scope.tenant_id,
                "project_id": record.scope.project_id,
                "project_revision": record.scope.project_revision,
            },
            "snapshot": {
                "snapshot_id": record.snapshot_id,
                "snapshot_hash": record.snapshot_hash,
            },
            "created_at": record.created_at.isoformat(),
            "status": report.get("status"),
            "evaluation_status": report.get("evaluation_status"),
            "summary": dict(summary) if isinstance(summary, Mapping) else {},
            "quality_index": dict(quality_index) if isinstance(quality_index, Mapping) else {},
        }


__all__ = [
    "SCHEDULE_QUALITY_AUDIT_HISTORY_VERSION",
    "ScheduleQualityAuditHistoryAPI",
]
