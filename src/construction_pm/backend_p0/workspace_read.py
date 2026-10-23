from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from construction_pm.application.authorization import AuthorizationContext, AuthorizationPolicy, Permission
from construction_pm.activity_master_repository import ActivityMasterRepository, ActivityPersistenceError
from construction_pm.wbs_master_repository import WBSMasterRepository, WBSPersistenceError

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
WORKSPACE_CONTROL_ROOM_READ_V2_VERSION = "workspace-control-room-read.v2"
WORKSPACE_CONTROL_ROOM_READ_V2_PATH = "/api/v2/workspace/control-room/read"
WORKSPACE_CONTROL_ROOM_V2_VERSION = "workspace-control-room.v2"


class WorkspaceReadProvider(Protocol):
    def read(self, scope: BackendScope) -> Mapping[str, object] | None: ...


class InMemoryWorkspaceReadProvider:
    """Reference adapter; authoritative values are supplied by the caller/read model."""

    def __init__(self, snapshots: Mapping[tuple[str, str, int], Mapping[str, object]] | None = None) -> None:
        self._snapshots = dict(snapshots or {})

    def read(self, scope: BackendScope) -> Mapping[str, object] | None:
        return self._snapshots.get((scope.tenant_id, scope.project_id, scope.project_revision))


class PersistedWBSWorkspaceReadProvider:
    """Build workspace v2 from persisted WBS/Activity data without inventing schedule values."""

    def __init__(
        self,
        activity_repository: ActivityMasterRepository,
        wbs_repository: WBSMasterRepository,
    ) -> None:
        self.activity_repository = activity_repository
        self.wbs_repository = wbs_repository

    def read(self, scope: BackendScope) -> Mapping[str, object]:
        scope.validate()
        try:
            wbs_records = self.wbs_repository.list(scope)
            activities = self.activity_repository.list(scope)
        except (ActivityPersistenceError, WBSPersistenceError) as exc:
            code = str(exc) or "WORKSPACE_PERSISTENCE_READ_FAILED"
            category = ErrorCategory.CONFLICT if code == "REVISION_CONFLICT" else ErrorCategory.VALIDATION
            raise BackendApplicationError(
                category,
                code,
                "Persisted Activity/WBS data could not be read consistently for this project revision",
                retryable=category is ErrorCategory.CONFLICT,
            ) from exc
        wbs_by_id = {node.wbs_id: node for node in wbs_records}
        if len(wbs_by_id) != len(wbs_records):
            raise BackendApplicationError(
                ErrorCategory.VALIDATION,
                "DUPLICATE_WORKSPACE_WBS_ID",
                "Persisted WBS IDs must be unique within the requested scope",
            )

        wbs_nodes = [
            {
                "wbs_id": node.wbs_id,
                "parent_kind": node.parent_kind.value,
                "parent_wbs_id": node.parent_wbs_id,
                "local_code": node.code,
                "name": node.name,
                "sequence_number": node.sequence_number,
                "record_revision": node.record_revision,
            }
            for node in wbs_records
        ]
        workspace_activities: list[dict[str, object]] = []
        for activity in activities:
            if not activity.wbs_id:
                raise BackendApplicationError(
                    ErrorCategory.VALIDATION,
                    "ACTIVITY_WBS_REQUIRED",
                    "An activity without a canonical WBS assignment cannot be published to the workspace",
                )
            if activity.wbs_id not in wbs_by_id:
                raise BackendApplicationError(
                    ErrorCategory.VALIDATION,
                    "ACTIVITY_WBS_REFERENCE_INVALID",
                    "Activity WBS must resolve inside the requested project revision",
                )
            if not activity.name.strip():
                raise BackendApplicationError(
                    ErrorCategory.VALIDATION,
                    "INVALID_WORKSPACE_ACTIVITY_NAME",
                    "Activity names are required for workspace publication",
                )
            workspace_activities.append({
                "id": activity.activity_id,
                "wbs_id": activity.wbs_id,
                # Activity ID is not the distinct P6 Activity Code field.
                "code": "",
                "name": activity.name,
                "cells": {
                    "activity_id": activity.activity_id,
                    "activity_code": None,
                    "activity_name": activity.name,
                    "start": None,
                    "finish": None,
                    "duration": str(activity.duration_value),
                    "progress": activity.percent_complete,
                },
                # Gantt data is supplied only by the authoritative schedule result.
                "gantt": None,
            })

        scope_dto = {
            "tenant_id": scope.tenant_id,
            "project_id": scope.project_id,
            "revision": scope.project_revision,
        }
        columns = [
            {"id": "activity_id", "label": "Activity ID", "data_type": "text", "editable": False, "formula": None, "width": 120},
            {"id": "activity_code", "label": "Code", "data_type": "text", "editable": False, "formula": None, "width": 100},
            {"id": "activity_name", "label": "Activity Name", "data_type": "text", "editable": False, "formula": None, "width": 260},
            {"id": "start", "label": "Start", "data_type": "date", "editable": False, "formula": None, "width": 120},
            {"id": "finish", "label": "Finish", "data_type": "date", "editable": False, "formula": None, "width": 120},
            {"id": "duration", "label": "Duration", "data_type": "duration", "editable": False, "formula": None, "width": 110},
            {"id": "progress", "label": "Progress", "data_type": "decimal", "editable": False, "formula": None, "width": 100},
        ]
        return {
            "contract_version": WORKSPACE_CONTROL_ROOM_READ_V2_VERSION,
            "context": scope_dto,
            "workspace": {
                "contract_version": WORKSPACE_CONTROL_ROOM_V2_VERSION,
                "context": dict(scope_dto),
                "columns": columns,
                "activities": workspace_activities,
                "wbs_nodes": wbs_nodes,
            },
            "control_intelligence": None,
            "field_daily_logs": [],
            "field_issues": [],
            "field_timecards": [],
            "equipment_status_reports": [],
            "inspections": [],
            "quality_records": [],
            "safety_observations": [],
            "punch_items": [],
        }


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
        read_version = snapshot.get("contract_version")
        if read_version not in (
            WORKSPACE_CONTROL_ROOM_READ_VERSION,
            WORKSPACE_CONTROL_ROOM_READ_V2_VERSION,
        ):
            raise BackendApplicationError(
                ErrorCategory.VALIDATION,
                "UNSUPPORTED_WORKSPACE_READ_CONTRACT",
                "Workspace control-room read contract version is not supported",
            )
        is_v2 = read_version == WORKSPACE_CONTROL_ROOM_READ_V2_VERSION

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

        workspace = snapshot.get("workspace")
        if not isinstance(workspace, Mapping):
            raise BackendApplicationError(
                ErrorCategory.VALIDATION,
                "INVALID_WORKSPACE_READ_WORKSPACE",
                "Workspace control-room payload is invalid",
            )
        expected_workspace_version = (
            WORKSPACE_CONTROL_ROOM_V2_VERSION if is_v2 else "workspace-control-room.v1"
        )
        if workspace.get("contract_version") != expected_workspace_version:
            raise BackendApplicationError(
                ErrorCategory.VALIDATION,
                "UNSUPPORTED_WORKSPACE_CONTRACT",
                "Workspace control-room contract version is not supported",
            )

        workspace_context = workspace.get("context")
        if not isinstance(workspace_context, Mapping):
            raise BackendApplicationError(
                ErrorCategory.VALIDATION,
                "INVALID_WORKSPACE_SNAPSHOT_CONTEXT",
                "Workspace control-room context is invalid",
            )
        if (
            workspace_context.get("tenant_id") != scope.tenant_id
            or workspace_context.get("project_id") != scope.project_id
            or workspace_context.get("revision") != scope.project_revision
        ):
            raise BackendApplicationError(
                ErrorCategory.CONFLICT,
                "STALE_WORKSPACE_SNAPSHOT_SCOPE",
                "Workspace control-room snapshot does not match the requested scope",
                retryable=True,
            )

        for key in ("columns", "activities"):
            if not isinstance(workspace.get(key), list):
                raise BackendApplicationError(
                    ErrorCategory.VALIDATION,
                    "INVALID_WORKSPACE_READ_WORKSPACE_COLLECTION",
                    f"Workspace control-room {key} collection is invalid",
                )

        if is_v2:
            nodes = workspace.get("wbs_nodes")
            if not isinstance(nodes, list):
                raise BackendApplicationError(
                    ErrorCategory.VALIDATION,
                    "INVALID_WORKSPACE_WBS_COLLECTION",
                    "Workspace v2 must include the canonical WBS node collection",
                )
            nodes_by_id: dict[str, Mapping[str, object]] = {}
            roots = 0
            for node in nodes:
                if not isinstance(node, Mapping):
                    raise BackendApplicationError(
                        ErrorCategory.VALIDATION, "INVALID_WORKSPACE_WBS_NODE",
                        "Workspace WBS nodes must be objects",
                    )
                node_id = node.get("wbs_id")
                parent_kind = node.get("parent_kind")
                parent_id = node.get("parent_wbs_id")
                local_code = node.get("local_code")
                node_name = node.get("name")
                sequence_number = node.get("sequence_number")
                if (
                    not isinstance(node_id, str) or not node_id.strip()
                    or node_id in nodes_by_id
                    or parent_kind not in ("project", "wbs")
                    or not isinstance(local_code, str) or not local_code.strip()
                    or not isinstance(node_name, str) or not node_name.strip()
                    or isinstance(sequence_number, bool)
                    or not isinstance(sequence_number, int) or sequence_number < 0
                ):
                    raise BackendApplicationError(
                        ErrorCategory.VALIDATION, "INVALID_WORKSPACE_WBS_NODE",
                        "Workspace WBS node fields or identity are invalid",
                    )
                if parent_kind == "project":
                    if parent_id is not None:
                        raise BackendApplicationError(
                            ErrorCategory.VALIDATION, "INVALID_WORKSPACE_WBS_PARENT",
                            "Project-root WBS nodes cannot reference a WBS parent",
                        )
                    roots += 1
                elif not isinstance(parent_id, str) or not parent_id.strip() or parent_id == node_id:
                    raise BackendApplicationError(
                        ErrorCategory.VALIDATION, "INVALID_WORKSPACE_WBS_PARENT",
                        "Child WBS nodes require a distinct parent WBS ID",
                    )
                nodes_by_id[node_id] = node
            if nodes and roots != 1:
                raise BackendApplicationError(
                    ErrorCategory.VALIDATION, "INVALID_WORKSPACE_WBS_ROOT",
                    "A non-empty WBS hierarchy must have exactly one project root",
                )
            for node in nodes_by_id.values():
                if node.get("parent_kind") == "wbs" and node.get("parent_wbs_id") not in nodes_by_id:
                    raise BackendApplicationError(
                        ErrorCategory.VALIDATION, "INVALID_WORKSPACE_WBS_PARENT",
                        "Every child WBS parent must exist in the same read snapshot",
                    )
                visited: set[str] = set()
                current_id = node.get("wbs_id")
                while isinstance(current_id, str):
                    if current_id in visited:
                        raise BackendApplicationError(
                            ErrorCategory.VALIDATION, "WORKSPACE_WBS_CYCLE",
                            "Workspace WBS hierarchy cannot contain cycles",
                        )
                    visited.add(current_id)
                    current_node = nodes_by_id.get(current_id)
                    if current_node is None or current_node.get("parent_kind") != "wbs":
                        break
                    parent_id = current_node.get("parent_wbs_id")
                    current_id = parent_id if isinstance(parent_id, str) else None
            activity_ids: set[str] = set()
            for activity in workspace["activities"]:
                if not isinstance(activity, Mapping):
                    raise BackendApplicationError(
                        ErrorCategory.VALIDATION, "INVALID_WORKSPACE_ACTIVITY",
                        "Workspace activity rows must be objects",
                    )
                activity_id = activity.get("id")
                wbs_id = activity.get("wbs_id")
                name = activity.get("name")
                if (
                    not isinstance(activity_id, str) or not activity_id.strip()
                    or activity_id in activity_ids
                    or not isinstance(name, str) or not name.strip()
                    or not isinstance(wbs_id, str) or wbs_id not in nodes_by_id
                ):
                    raise BackendApplicationError(
                        ErrorCategory.VALIDATION, "INVALID_WORKSPACE_ACTIVITY_WBS",
                        "Every workspace activity must reference one canonical WBS node in this snapshot",
                    )
                activity_ids.add(activity_id)

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
    "WORKSPACE_CONTROL_ROOM_READ_V2_PATH",
    "WORKSPACE_CONTROL_ROOM_READ_V2_VERSION",
    "WORKSPACE_CONTROL_ROOM_V2_VERSION",
    "WorkspaceControlRoomReadService",
    "WorkspaceReadProvider",
    "InMemoryWorkspaceReadProvider",
    "PersistedWBSWorkspaceReadProvider",
]
