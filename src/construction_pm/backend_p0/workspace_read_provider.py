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

from .models import BackendScope
from .workspace_read import WORKSPACE_CONTROL_ROOM_READ_VERSION


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
        activity_rows = [
            _activity_payload(activity, facts, self.wbs_by_activity)
            for activity in activities
        ]
        return {
            "contract_version": WORKSPACE_CONTROL_ROOM_READ_VERSION,
            "context": _scope_payload(scope),
            "workspace": {
                "contract_version": WORKSPACE_CONTROL_ROOM_CONTRACT_VERSION,
                "context": _scope_payload(scope),
                "columns": columns,
                "activities": activity_rows,
                # Rollup navigation over the persisted WBS assignment. Every
                # value is an aggregate of the same authoritative activity and
                # schedule-fact rows above; no date is calculated here.
                "wbs_summary": _wbs_summary(activity_rows),
            },
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


def _wbs_summary(
    activity_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Aggregate persisted WBS assignments for navigation.

    The summary contains only counts and bounds of values already projected
    from authoritative facts. It never derives a schedule date.
    """

    groups: dict[str, dict[str, object]] = {}
    for row in activity_rows:
        wbs_id = row["wbs_id"]
        if not isinstance(wbs_id, str):
            raise ValueError("INVALID_WORKSPACE_WBS_ID")
        group = groups.get(wbs_id)
        if group is None:
            group = {
                "wbs_id": wbs_id,
                "activity_count": 0,
                "critical_count": 0,
                "scheduled_start": None,
                "scheduled_finish": None,
                "total_float_min": None,
            }
            groups[wbs_id] = group
        group["activity_count"] = int(group["activity_count"]) + 1
        gantt = row.get("gantt")
        if isinstance(gantt, Mapping):
            start = gantt.get("start")
            finish = gantt.get("finish")
            if not isinstance(start, str) or not isinstance(finish, str):
                raise ValueError("INVALID_WORKSPACE_WBS_SCHEDULE_BOUNDS")
            current_start = group["scheduled_start"]
            current_finish = group["scheduled_finish"]
            if current_start is None or start < str(current_start):
                group["scheduled_start"] = start
            if current_finish is None or finish > str(current_finish):
                group["scheduled_finish"] = finish
            if gantt.get("critical") is True:
                group["critical_count"] = int(group["critical_count"]) + 1
        cells = row.get("cells")
        if isinstance(cells, Mapping):
            total_float = cells.get("activity.total_float")
            if isinstance(total_float, int) and not isinstance(total_float, bool):
                current_float = group["total_float_min"]
                if current_float is None or total_float < int(current_float):
                    group["total_float_min"] = total_float
    return list(groups.values())


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


def _activity_payload(
    activity: ActivityMaster,
    facts: Mapping[str, object],
    wbs_by_activity: Mapping[str, str],
) -> dict[str, object]:
    display_name = activity.name.strip() or activity.activity_id
    wbs = wbs_by_activity.get(activity.activity_id, "UNASSIGNED")
    cells: dict[str, object] = {
        # Canonical field-registry IDs drive the persisted layout. Legacy
        # activity.activity_* IDs remain populated for older saved layouts.
        "activity.id": activity.activity_id,
        "activity.name": display_name,
        "activity.status": _enum_text(activity.status),
        "activity.type": _enum_text(activity.activity_type),
        "activity.status_code": _enum_text(activity.status_code),
        "activity.leveling_priority": _enum_text(activity.leveling_priority),
        "activity.wbs": wbs,
        "activity.activity_id": activity.activity_id,
        "activity.activity_name": display_name,
        "activity.activity_status": _enum_text(activity.status),
        "activity.activity_type": _enum_text(activity.activity_type),
    }
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
        "wbs_id": wbs_by_activity.get(activity.activity_id, "UNASSIGNED"),
        "code": activity.activity_id,
        "name": activity.name.strip() or activity.activity_id,
        "cells": cells,
        "gantt": gantt,
    }


__all__ = [
    "PersistedWorkspaceReadProvider",
    "WorkspaceScheduleFactsProvider",
]
