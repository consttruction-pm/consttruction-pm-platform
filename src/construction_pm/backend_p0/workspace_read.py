from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from construction_pm.application.authorization import AuthorizationContext, AuthorizationPolicy, Permission

from .errors import BackendApplicationError, ErrorCategory
from .models import (
    BackendScope,
    ProcurementRFQ,
    ProcurementQuote,
    ProcurementBidComparison,
    PurchaseOrder,
    ProcurementCommitment,
    ProcurementDelivery,
)
from .repository import BackendP0Repository

WORKSPACE_CONTROL_ROOM_READ_VERSION = "workspace-control-room-read.v1"
WORKSPACE_CONTROL_ROOM_READ_PATH = "/api/v1/workspace/control-room/read"


class WorkspaceReadProvider(Protocol):
    def read(self, scope: BackendScope) -> Mapping[str, object] | None: ...


class InMemoryWorkspaceReadProvider:
    """Reference adapter; authoritative values are supplied by the caller/read model."""

    def __init__(self, snapshots: Mapping[tuple[str, str, int], Mapping[str, object]] | None = None) -> None:
        self._snapshots = dict(snapshots or {})

    def read(self, scope: BackendScope) -> Mapping[str, object] | None:
        return self._snapshots.get((scope.tenant_id, scope.project_id, scope.project_revision))


@dataclass(frozen=True)
class WorkspaceControlRoomReadService:
    provider: WorkspaceReadProvider
    authorization_policy: AuthorizationPolicy
    procurement_repository: BackendP0Repository | None = None

    def read(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, object] | None:
        scope.validate()
        if (
            auth_context.tenant_id != scope.tenant_id
            or auth_context.project_id != scope.project_id
        ):
            raise BackendApplicationError(
                ErrorCategory.AUTHORIZATION,
                "CROSS_SCOPE_ACCESS",
                "Authorization context does not match the workspace scope",
            )
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise BackendApplicationError(
                ErrorCategory.AUTHORIZATION,
                "FORBIDDEN",
                "Operation is not authorized",
            )

        snapshot = self.provider.read(scope)
        if snapshot is None:
            return None
        self._validate_snapshot(snapshot, scope)
        result = dict(snapshot)
        if self.procurement_repository is not None:
            procurement = self.procurement_repository.list_records(
                scope.tenant_id,
                scope.project_id,
                (
                    "procurement_rfq",
                    "procurement_quote",
                    "procurement_bid_comparison",
                    "purchase_order",
                    "procurement_commitment",
                    "procurement_delivery",
                ),
            )
            result.update({
                "procurement_rfqs": [stored.record.as_dict() for stored in procurement if stored.record.scope.project_revision == scope.project_revision and isinstance(stored.record, ProcurementRFQ)],
                "procurement_quotes": [stored.record.as_dict() for stored in procurement if stored.record.scope.project_revision == scope.project_revision and isinstance(stored.record, ProcurementQuote)],
                "procurement_bid_comparisons": [stored.record.as_dict() for stored in procurement if stored.record.scope.project_revision == scope.project_revision and isinstance(stored.record, ProcurementBidComparison)],
                "purchase_orders": [stored.record.as_dict() for stored in procurement if stored.record.scope.project_revision == scope.project_revision and isinstance(stored.record, PurchaseOrder)],
                "procurement_commitments": [stored.record.as_dict() for stored in procurement if stored.record.scope.project_revision == scope.project_revision and isinstance(stored.record, ProcurementCommitment)],
                "procurement_deliveries": [stored.record.as_dict() for stored in procurement if stored.record.scope.project_revision == scope.project_revision and isinstance(stored.record, ProcurementDelivery)],
            })
        return result

    @staticmethod
    def _validate_snapshot(
        snapshot: Mapping[str, object],
        scope: BackendScope,
    ) -> None:
        if snapshot.get("contract_version") != WORKSPACE_CONTROL_ROOM_READ_VERSION:
            raise BackendApplicationError(
                ErrorCategory.VALIDATION,
                "UNSUPPORTED_WORKSPACE_READ_CONTRACT",
                "Workspace read contract version is not supported",
            )

        context = snapshot.get("context")
        if not isinstance(context, Mapping):
            raise BackendApplicationError(
                ErrorCategory.VALIDATION,
                "INVALID_WORKSPACE_READ_CONTEXT",
                "Workspace read context is invalid",
            )

        if (
            context.get("tenant_id") != scope.tenant_id
            or context.get("project_id") != scope.project_id
            or context.get("revision") != scope.project_revision
        ):
            raise BackendApplicationError(
                ErrorCategory.CONFLICT,
                "STALE_WORKSPACE_READ_SCOPE",
                "Workspace snapshot revision does not match the requested scope",
                retryable=True,
            )

        for key in (
            "workspace",
            "field_daily_logs",
            "field_issues",
            "field_timecards",
            "equipment_status_reports",
            "inspections",
            "quality_records",
            "safety_observations",
            "punch_items",
        ):
            if key not in snapshot:
                raise BackendApplicationError(
                    ErrorCategory.VALIDATION,
                    "INVALID_WORKSPACE_READ",
                    f"Workspace read snapshot is missing {key}",
                )
        for key in (
            "field_daily_logs",
            "field_issues",
            "field_timecards",
            "equipment_status_reports",
            "inspections",
            "quality_records",
            "safety_observations",
            "punch_items",
        ):
            if not isinstance(snapshot[key], (list, tuple)):
                raise BackendApplicationError(
                    ErrorCategory.VALIDATION,
                    "INVALID_WORKSPACE_READ_COLLECTION",
                    f"Workspace read collection {key} is invalid",
                )

        for key in (
            "change_notices",
            "change_cases",
            "claims",
            "change_claim_impacts",
            "documents",
            "procurement_rfqs",
            "procurement_quotes",
            "procurement_bid_comparisons",
            "purchase_orders",
            "procurement_commitments",
            "procurement_deliveries",
        ):
            if key in snapshot and not isinstance(snapshot[key], (list, tuple)):
                raise BackendApplicationError(
                    ErrorCategory.VALIDATION,
                    "INVALID_WORKSPACE_READ_COLLECTION",
                    f"Workspace read collection {key} is invalid",
                )


__all__ = [
    "WORKSPACE_CONTROL_ROOM_READ_PATH",
    "WORKSPACE_CONTROL_ROOM_READ_VERSION",
    "WorkspaceControlRoomReadService",
    "WorkspaceReadProvider",
    "InMemoryWorkspaceReadProvider",
]
