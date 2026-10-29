from __future__ import annotations

"""Repository-backed projection of persisted activities into the Workspace read contract.

This adapter does not calculate dates. It joins three authoritative sources:

* Activity Master persistence for the activities that actually exist;
* persisted field/layout metadata for presentation only;
* a schedule-facts provider that projects the latest immutable snapshot through
  the Shared Domain/Calculation Core.

When no published snapshot exists the activities remain visible without dates.
When a snapshot exists but cannot be evaluated the error propagates, so a failed
calculation is never presented as an empty successful schedule.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Callable, Mapping

from construction_pm.activity_master_repository import ActivityMaster, ActivityMasterRepository
from construction_pm.application.authorization import AuthorizationContext
from construction_pm.p6_field_registry import P6FieldType
from construction_pm.p6_field_registry_repository import (
    P6FieldRegistryApplicationService,
    PersistedP6Field,
)
from construction_pm.p6_layout_definition_repository import (
    LayoutColumn,
    PersistedP6Layout,
    P6LayoutRepository,
)
from construction_pm.relationship_master_repository import (
    RelationshipMaster,
    RelationshipMasterRepository,
    RelationshipPersistenceError,
)
from construction_pm.wbs_master_repository import (
    WBSMaster,
    WBSMasterRepository,
    WBSPersistenceError,
)

from .errors import BackendApplicationError, ErrorCategory
from .models import BackendScope
from .workspace_read import (
    WORKSPACE_CONTROL_ROOM_READ_V2_VERSION,
    WORKSPACE_CONTROL_ROOM_READ_VERSION,
    WORKSPACE_CONTROL_ROOM_V2_VERSION,
)


WORKSPACE_CONTROL_ROOM_CONTRACT_VERSION = "workspace-control-room.v1"

# Callback contract: return the FACT projection of the latest published
# snapshot, or None when no snapshot has been published for this scope.
WorkspaceScheduleFactsProvider = Callable[
    [BackendScope, AuthorizationContext | None],
    Mapping[str, object] | None,
]

_DEFAULT_FIELD_IDS = (
    "activity.id",
    "activity.name",
    "activity.status",
    "activity.wbs",
    "activity.early_start",
    "activity.early_finish",
    "activity.total_float",
    "activity.is_critical",
)

_DATA_TYPE_MAP: dict[P6FieldType, str] = {
    P6FieldType.STRING: "text",
    P6FieldType.DATE: "date",
    P6FieldType.DATETIME: "datetime",
    P6FieldType.DURATION: "duration",
    P6FieldType.DECIMAL: "decimal",
    P6FieldType.PERCENTAGE: "percentage",
    P6FieldType.BOOLEAN: "boolean",
    P6FieldType.ENUM: "enum",
    P6FieldType.INTEGER: "integer",
    P6FieldType.DOUBLE: "double",
    P6FieldType.COST: "cost",
    P6FieldType.UNIT: "unit",
    P6FieldType.OBJECT_ID: "object-id",
    P6FieldType.OBJECT_ID_ARRAY: "object-id-array",
    P6FieldType.STRING_ARRAY: "string-array",
    P6FieldType.COMPLEX: "complex",
    P6FieldType.SPREAD: "spread",
}

_FALLBACK_COLUMNS: tuple[dict[str, object], ...] = (
    {"id": "activity_id", "label": "Activity ID", "data_type": "text", "editable": False, "formula": None, "width": 130},
    {"id": "activity_name", "label": "Activity Name", "data_type": "text", "editable": False, "formula": None, "width": 260},
    {"id": "start", "label": "Start", "data_type": "date", "editable": False, "formula": None, "width": 120},
    {"id": "finish", "label": "Finish", "data_type": "date", "editable": False, "formula": None, "width": 120},
    {"id": "duration", "label": "Duration", "data_type": "duration", "editable": False, "formula": None, "width": 110},
)


def _optional_iso(value: date | datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _decimal_text(value: Decimal | int | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("INVALID_WORKSPACE_ACTIVITY_NUMBER")
    return format(Decimal(str(value)), "f")


def _enum_text(value: object) -> str:
    return str(getattr(value, "value", value))


def _fact_rows(payload: Mapping[str, object]) -> Mapping[str, object]:
    rows = payload.get("activities")
    if not isinstance(rows, Mapping):
        raise ValueError("INVALID_SCHEDULE_FACTS_ACTIVITIES")
    return rows


@dataclass(frozen=True)
class PersistedWorkspaceReadProvider:
    """Build the versioned Workspace read envelope from persisted state.

    Field and layout repositories are presentation metadata only. They never
    supply a scheduled date, float or critical flag.
    """

    activity_repository: ActivityMasterRepository
    field_service: P6FieldRegistryApplicationService | None = None
    layout_repository: P6LayoutRepository | None = None
    schedule_facts_provider: WorkspaceScheduleFactsProvider | None = None
    wbs_repository: WBSMasterRepository | None = None
    relationship_repository: RelationshipMasterRepository | None = None
    wbs_by_activity: Mapping[str, str] = field(default_factory=dict)
    registry_version: str = "p6-field-registry.v1"
    layout_scope: str = "project"
    view_id: str = "activity"

    def read(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext | None = None,
    ) -> Mapping[str, object] | None:
        scope.validate()
        activities = self.activity_repository.list(scope)
        fields = self._fields(scope)
        layout = self._layout(scope)
        columns = _columns(fields, layout)
        facts = self._facts(scope, auth_context)
        wbs_records = self._wbs_records(scope)
        canonical_wbs = self.wbs_repository is not None
        wbs_by_id = {node.wbs_id: node for node in wbs_records}
        activity_ids = {activity.activity_id for activity in activities}
        if canonical_wbs:
            if len(wbs_by_id) != len(wbs_records):
                raise BackendApplicationError(
                    ErrorCategory.VALIDATION,
                    "DUPLICATE_WORKSPACE_WBS_ID",
                    "Persisted WBS IDs must be unique within the requested scope",
                )
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
        workspace: dict[str, object] = {
            "contract_version": (
                WORKSPACE_CONTROL_ROOM_V2_VERSION
                if canonical_wbs
                else WORKSPACE_CONTROL_ROOM_CONTRACT_VERSION
            ),
            "context": _scope_payload(scope),
            "columns": columns,
            "activities": [
                _activity_payload(
                    activity,
                    facts,
                    self.wbs_by_activity,
                    wbs_by_id if canonical_wbs else None,
                )
                for activity in activities
            ],
        }
        if canonical_wbs:
            workspace["wbs_nodes"] = [_wbs_node_payload(node) for node in wbs_records]
            if self.relationship_repository is not None:
                workspace["relationships"] = self._relationship_records(scope, activity_ids)
        return {
            "contract_version": (
                WORKSPACE_CONTROL_ROOM_READ_V2_VERSION
                if canonical_wbs
                else WORKSPACE_CONTROL_ROOM_READ_VERSION
            ),
            "context": _scope_payload(scope),
            "workspace": workspace,
            "field_daily_logs": [],
            "field_issues": [],
            "field_timecards": [],
            "equipment_status_reports": [],
            "inspections": [],
            "quality_records": [],
            "safety_observations": [],
            "punch_items": [],
            "change_notices": [],
            "change_cases": [],
            "claims": [],
            "change_claim_impacts": [],
            "documents": [],
            "procurement_rfqs": [],
            "procurement_quotes": [],
            "procurement_bid_comparisons": [],
            "purchase_orders": [],
            "procurement_commitments": [],
            "procurement_deliveries": [],
        }

    def _wbs_records(self, scope: BackendScope) -> tuple[WBSMaster, ...]:
        if self.wbs_repository is None:
            return ()
        try:
            return self.wbs_repository.list(scope)
        except WBSPersistenceError as exc:
            code = str(exc) or "WORKSPACE_WBS_READ_FAILED"
            category = (
                ErrorCategory.CONFLICT
                if code == "REVISION_CONFLICT"
                else ErrorCategory.VALIDATION
            )
            raise BackendApplicationError(
                category,
                code,
                "Persisted WBS data could not be read consistently for this project revision",
                retryable=category is ErrorCategory.CONFLICT,
            ) from exc

    def _relationship_records(
        self,
        scope: BackendScope,
        activity_ids: set[str],
    ) -> list[dict[str, object]]:
        """Project persisted logic links without calculating anything.

        A link whose endpoint is not an activity of this exact project
        revision fails closed: the workspace never hides orphaned logic.
        """
        if self.relationship_repository is None:
            return []
        try:
            records = self.relationship_repository.list(scope)
        except RelationshipPersistenceError as exc:
            code = str(exc) or "WORKSPACE_RELATIONSHIP_READ_FAILED"
            category = (
                ErrorCategory.CONFLICT
                if code == "REVISION_CONFLICT"
                else ErrorCategory.VALIDATION
            )
            raise BackendApplicationError(
                category,
                code,
                "Persisted relationships could not be read consistently for this project revision",
                retryable=category is ErrorCategory.CONFLICT,
            ) from exc
        payload: list[dict[str, object]] = []
        for record in records:
            if record.predecessor_id not in activity_ids or record.successor_id not in activity_ids:
                raise BackendApplicationError(
                    ErrorCategory.VALIDATION,
                    "RELATIONSHIP_REFERENCE_INVALID",
                    "A relationship endpoint must resolve inside the requested project revision",
                )
            payload.append(_relationship_payload(record))
        return payload

    def _fields(self, scope: BackendScope) -> tuple[PersistedP6Field, ...]:
        if self.field_service is None:
            return ()
        return self.field_service.list_fields(scope, self.registry_version, "Activity")

    def _layout(self, scope: BackendScope) -> PersistedP6Layout | None:
        if self.layout_repository is None:
            return None
        return self.layout_repository.get(scope, self.layout_scope, self.view_id)

    def _facts(
        self,
        scope: BackendScope,
        auth_context: AuthorizationContext | None,
    ) -> Mapping[str, object]:
        if self.schedule_facts_provider is None:
            return {}
        payload = self.schedule_facts_provider(scope, auth_context)
        if payload is None:
            # No snapshot has been published. The workspace still exposes the
            # persisted activities, but no calculated date is fabricated.
            return {}
        return _fact_rows(payload)


def _scope_payload(scope: BackendScope) -> dict[str, object]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "revision": scope.project_revision,
    }


def _columns(
    fields: tuple[PersistedP6Field, ...],
    layout: PersistedP6Layout | None,
) -> list[dict[str, object]]:
    by_id = {item.field.field_id: item.field for item in fields}
    if layout is not None and layout.columns:
        return [_column_from_layout(column, by_id) for column in layout.columns]
    if by_id:
        identifiers = [field_id for field_id in _DEFAULT_FIELD_IDS if field_id in by_id]
        if not identifiers:
            identifiers = list(by_id)[:10]
        return [_column_from_field(by_id[field_id], index) for index, field_id in enumerate(identifiers)]
    # This fallback keeps the contract syntactically valid. The Web bootstrap
    # still requires an authoritative field registry before it renders, so a
    # missing registry is reported there rather than hidden here.
    return [dict(column) for column in _FALLBACK_COLUMNS]


def _column_from_layout(
    column: LayoutColumn,
    by_id: Mapping[str, object],
) -> dict[str, object]:
    definition = by_id.get(column.field_id)
    if definition is None:
        label = column.label or column.field_id
        data_type = "text"
        editable = False
    else:
        label = column.label or definition.display_name
        data_type = _DATA_TYPE_MAP.get(definition.data_type, "text")
        editable = bool(definition.writable and not definition.computed)
    return {
        "id": column.field_id,
        "label": label,
        "data_type": data_type,
        "editable": editable,
        "formula": None,
        "width": column.width,
    }


def _column_from_field(definition, order: int) -> dict[str, object]:
    return {
        "id": definition.field_id,
        "label": definition.display_name,
        "data_type": _DATA_TYPE_MAP.get(definition.data_type, "text"),
        "editable": bool(definition.writable and not definition.computed),
        "formula": None,
        "width": 140 if order > 1 else 220,
    }


def _wbs_node_payload(node: WBSMaster) -> dict[str, object]:
    return {
        "wbs_id": node.wbs_id,
        "parent_kind": node.parent_kind.value,
        "parent_wbs_id": node.parent_wbs_id,
        "local_code": node.code,
        "name": node.name,
        "sequence_number": node.sequence_number,
        "record_revision": node.record_revision,
    }


def _relationship_payload(record: RelationshipMaster) -> dict[str, object]:
    return {
        "relationship_id": record.relationship_id,
        "predecessor_id": record.predecessor_id,
        "successor_id": record.successor_id,
        "relationship_type": record.relationship_type.value,
        "lag_value": format(record.lag_value, "f"),
        "lag_unit": record.lag_unit.value,
        "record_revision": record.record_revision,
    }


def _activity_payload(
    activity: ActivityMaster,
    facts: Mapping[str, object],
    wbs_by_activity: Mapping[str, str],
    wbs_nodes: Mapping[str, WBSMaster] | None = None,
) -> dict[str, object]:
    display_name = activity.name.strip() or activity.activity_id
    if wbs_nodes is not None:
        node = wbs_nodes.get(activity.wbs_id or "")
        if node is None:
            # Canonical mode validates the assignment before this projection.
            raise BackendApplicationError(
                ErrorCategory.VALIDATION,
                "ACTIVITY_WBS_REFERENCE_INVALID",
                "Activity WBS must resolve inside the requested project revision",
            )
        wbs_id = node.wbs_id
        wbs_display = f"{node.code} {node.name}"
    else:
        wbs_id = wbs_by_activity.get(activity.activity_id, "UNASSIGNED")
        wbs_display = wbs_by_activity.get(activity.activity_id, "UNASSIGNED")
    cells: dict[str, object] = {
        # Canonical field-registry IDs drive the persisted layout. Legacy
        # activity.activity_* IDs remain populated for older saved layouts.
        "activity.id": activity.activity_id,
        "activity.name": display_name,
        "activity.status": _enum_text(activity.status),
        "activity.type": _enum_text(activity.activity_type),
        "activity.status_code": _enum_text(activity.status_code),
        "activity.leveling_priority": _enum_text(activity.leveling_priority),
        "activity.wbs": wbs_display,
        "activity.activity_id": activity.activity_id,
        "activity.activity_name": display_name,
        "activity.activity_status": _enum_text(activity.status),
        "activity.activity_type": _enum_text(activity.activity_type),
        # Generic grid aliases expose persisted values only; no schedule result
        # is inferred when no authoritative snapshot has been published.
        "duration": _decimal_text(activity.duration_value),
    }
    if activity.percent_complete is not None:
        cells["progress"] = activity.percent_complete
    for field_id, value in (
        ("activity.planned_finish", _optional_iso(activity.planned_finish)),
        ("activity.actual_start", _optional_iso(activity.actual_start)),
        ("activity.actual_finish", _optional_iso(activity.actual_finish)),
        ("activity.remaining_start", _optional_iso(activity.remaining_start)),
        ("activity.expected_finish", _optional_iso(activity.expected_finish)),
        ("activity.planned_duration", _decimal_text(activity.duration_value)),
        ("activity.duration_percent_complete", activity.percent_complete),
    ):
        if value is not None:
            cells[field_id] = value
    if activity.remaining_duration is not None:
        cells["activity.remaining_duration"] = activity.remaining_duration

    fact = facts.get(activity.activity_id)
    gantt = None
    if isinstance(fact, Mapping):
        start = fact.get("start")
        finish = fact.get("finish")
        critical = fact.get("critical")
        if not isinstance(start, str) or not start.strip():
            raise ValueError("INVALID_SCHEDULE_FACT_START")
        if not isinstance(finish, str) or not finish.strip():
            raise ValueError("INVALID_SCHEDULE_FACT_FINISH")
        if not isinstance(critical, bool):
            # Criticality is only displayed when returned by the schedule
            # service. A missing flag must not silently become "not critical".
            raise ValueError("INVALID_SCHEDULE_FACT_CRITICAL")
        progress = activity.percent_complete if activity.percent_complete is not None else 0
        gantt = {
            "start": start,
            "finish": finish,
            "progressPercent": progress,
            "critical": critical,
        }
        cells["start"] = start
        cells["finish"] = finish
        for fact_key, field_id in (
            ("early_start", "activity.early_start"),
            ("early_finish", "activity.early_finish"),
            ("late_start", "activity.late_start"),
            ("late_finish", "activity.late_finish"),
            ("total_float", "activity.total_float"),
            ("free_float", "activity.free_float"),
        ):
            value = fact.get(fact_key)
            if isinstance(value, str):
                cells[field_id] = value
            elif isinstance(value, int) and not isinstance(value, bool):
                cells[field_id] = value
            elif value is not None:
                raise ValueError("INVALID_SCHEDULE_FACT_VALUE")
        cells["activity.is_critical"] = critical
        duration = fact.get("duration")
        if isinstance(duration, int) and not isinstance(duration, bool):
            # Scheduled duration is a display fact for the generic grid column;
            # persisted Planned Duration remains the Activity Master value.
            cells["duration"] = duration
    return {
        "id": activity.activity_id,
        "wbs_id": wbs_id,
        "code": activity.activity_id,
        "name": activity.name.strip() or activity.activity_id,
        "cells": cells,
        "gantt": gantt,
    }


__all__ = [
    "PersistedWorkspaceReadProvider",
    "WorkspaceScheduleFactsProvider",
]
