from __future__ import annotations

"""Bounded, scope-checked project facts for the local engineering assistant.

This module only projects persisted workspace data. It does not compute schedule,
risk, cost, quantities, progress, or capacity values.
"""

import json
import math
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any


PROJECT_CONTEXT_CONTRACT = "cubi-assistant-project-context.v1"
WORKSPACE_READ_CONTRACT = "workspace-control-room-read.v1"
WORKSPACE_CONTRACT = "workspace-control-room.v1"
MAX_CONTEXT_CHARS = 12_000
MAX_ACTIVITY_ROWS = 40
MAX_RECORDS_PER_COLLECTION = 3
MAX_TEXT_CHARS = 220

_ACTIVITY_FIELDS = (
    ("activity.id", "id"),
    ("activity.name", "name"),
    ("activity.wbs", "wbs"),
    ("activity.status", "status"),
    ("activity.type", "type"),
    ("activity.status_code", "status_code"),
    ("activity.planned_duration", "planned_duration"),
    ("activity.remaining_duration", "remaining_duration"),
    ("activity.duration_percent_complete", "duration_percent_complete"),
    ("activity.actual_start", "actual_start"),
    ("activity.actual_finish", "actual_finish"),
    ("start", "start"),
    ("finish", "finish"),
    ("activity.early_start", "early_start"),
    ("activity.early_finish", "early_finish"),
    ("activity.late_start", "late_start"),
    ("activity.late_finish", "late_finish"),
    ("activity.total_float", "total_float"),
    ("activity.free_float", "free_float"),
    ("activity.is_critical", "critical"),
)

_RECORD_COLLECTIONS = (
    "field_daily_logs",
    "field_issues",
    "field_timecards",
    "equipment_status_reports",
    "inspections",
    "quality_records",
    "safety_observations",
    "punch_items",
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
)

_RECORD_FIELDS = frozenset({
    "id", "record_id", "issue_id", "log_id", "inspection_id", "observation_id",
    "report_id", "claim_id", "notice_id", "case_id", "document_id", "item_id",
    "rfq_id", "quote_id", "comparison_id", "po_id", "commitment_id", "delivery_id",
    "code", "title", "name", "description", "summary", "status", "category",
    "severity", "likelihood", "impact", "priority", "activity_id", "activity_ids",
    "wbs_id", "wbs", "due_date", "observed_at", "created_at", "date", "reported_at",
    "start_date", "finish_date", "planned_finish", "actual_finish", "quantity", "unit",
    "resource_id", "equipment_id", "issue_type", "risk_type", "consequence",
    "mitigation", "corrective_action", "trigger", "source_ref", "revision",
    "approved", "note", "notes", "observation", "action", "recommendation", "cause",
    "responsible_role", "owner_role", "location",
})
_RECORD_FIELD_ORDER = (
    "id", "record_id", "issue_id", "log_id", "inspection_id", "observation_id",
    "report_id", "claim_id", "notice_id", "case_id", "document_id", "item_id",
    "rfq_id", "quote_id", "comparison_id", "po_id", "commitment_id", "delivery_id",
    "code", "title", "name", "status", "category", "severity", "priority",
    "risk_type", "issue_type", "activity_id", "activity_ids", "wbs_id", "wbs",
    "description", "summary", "observation", "consequence", "trigger",
    "corrective_action", "mitigation", "recommendation", "action", "cause",
    "due_date", "observed_at", "reported_at", "date", "start_date", "finish_date",
    "planned_finish", "actual_finish", "resource_id", "equipment_id", "quantity",
    "unit", "source_ref", "revision", "approved", "responsible_role", "owner_role",
    "location", "created_at", "note", "notes", "likelihood", "impact",
)


class AIProjectContextError(ValueError):
    """Stable error for malformed or out-of-scope assistant context."""


def _scope_matches(value: object, *, tenant_id: str, project_id: str, revision: int) -> bool:
    if not isinstance(value, Mapping):
        return False
    return (
        value.get("tenant_id") == tenant_id
        and value.get("project_id") == project_id
        and value.get("revision") == revision
    )


def _safe_value(value: object) -> object:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise AIProjectContextError("AI_PROJECT_CONTEXT_NUMBER_INVALID")
        return value
    if isinstance(value, str):
        return value.strip()[:MAX_TEXT_CHARS]
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value[:8] if isinstance(item, (str, int, float, bool)) or item is None]
    return None


def _activity_rows(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        raise AIProjectContextError("AI_PROJECT_CONTEXT_ACTIVITIES_INVALID")
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for source in raw:
        if not isinstance(source, Mapping):
            raise AIProjectContextError("AI_PROJECT_CONTEXT_ACTIVITY_INVALID")
        cells = source.get("cells")
        if not isinstance(cells, Mapping):
            raise AIProjectContextError("AI_PROJECT_CONTEXT_ACTIVITY_CELLS_INVALID")
        activity_id = cells.get("activity.id", source.get("id"))
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise AIProjectContextError("AI_PROJECT_CONTEXT_ACTIVITY_ID_INVALID")
        activity_id = activity_id.strip()[:128]
        if activity_id in seen:
            raise AIProjectContextError("AI_PROJECT_CONTEXT_ACTIVITY_DUPLICATE")
        seen.add(activity_id)
        row: dict[str, object] = {"id": activity_id}
        for field_id, output_name in _ACTIVITY_FIELDS:
            if output_name == "id" or field_id not in cells:
                continue
            value = cells[field_id]
            if value is None:
                continue
            if output_name == "critical" and not isinstance(value, bool):
                raise AIProjectContextError("AI_PROJECT_CONTEXT_CRITICALITY_INVALID")
            safe = _safe_value(value)
            if safe is not None:
                row[output_name] = safe
        row["schedule_facts_available"] = all(
            key in row for key in ("start", "finish", "critical")
        )
        rows.append(row)
    return rows


def _record_rows(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, (list, tuple)):
        raise AIProjectContextError("AI_PROJECT_CONTEXT_RECORD_COLLECTION_INVALID")
    rows: list[dict[str, object]] = []
    for source in raw[:MAX_RECORDS_PER_COLLECTION]:
        if not isinstance(source, Mapping):
            continue
        record: dict[str, object] = {}
        for key in _RECORD_FIELD_ORDER:
            if key not in source or key not in _RECORD_FIELDS or len(record) >= 16:
                continue
            safe = _safe_value(source[key])
            if safe is not None:
                record[key] = safe
        if record:
            rows.append(record)
    return rows


_OPEN_STATUSES = frozenset({
    "open", "new", "unresolved", "in_progress", "pending", "requires_action",
})
_EQUIPMENT_FAILURE_STATUSES = frozenset({
    "down", "failed", "broken", "out_of_service", "unavailable",
    "maintenance_required",
})
_QUALITY_FAILURE_STATUSES = frozenset({
    "failed", "rejected", "nonconforming", "defect", "open", "requires_action",
})


def _finite_decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _record_id(record: Mapping[str, object]) -> str | None:
    for key in (
        "issue_id", "record_id", "log_id", "inspection_id", "observation_id",
        "report_id", "claim_id", "notice_id", "case_id", "item_id", "id",
    ):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:128]
    return None


def _engineering_signals(
    activities: list[dict[str, object]],
    snapshot: Mapping[str, object],
    project_revision: int,
) -> tuple[list[dict[str, object]], dict[str, int], bool]:
    """Detect explicit review triggers only; never assigns probability or impact."""
    signals: list[dict[str, object]] = []
    signals_truncated = False

    def add(signal: dict[str, object]) -> None:
        nonlocal signals_truncated
        if len(signals) < 20:
            signals.append(signal)
        else:
            signals_truncated = True

    for activity in activities:
        activity_id = str(activity["id"])
        float_value = activity.get("total_float")
        float_number = _finite_decimal(float_value)
        if float_number is not None and float_number < 0:
            add({
                "signal_type": "negative_total_float",
                "classification": "schedule_warning_candidate",
                "status": "needs_review",
                "project_revision": project_revision,
                "activity_id": activity_id,
                "basis_fields": {"activity.total_float": float_value},
                "evidence_contract": WORKSPACE_READ_CONTRACT,
            })
        percent = _finite_decimal(activity.get("duration_percent_complete"))
        if (
            activity.get("critical") is True
            and activity.get("schedule_facts_available") is True
            and percent is not None
            and Decimal("0") <= percent < Decimal("100")
            and not activity.get("actual_finish")
        ):
            add({
                "signal_type": "unfinished_critical_activity",
                "classification": "schedule_watch_candidate",
                "status": "needs_review",
                "project_revision": project_revision,
                "activity_id": activity_id,
                "basis_fields": {
                    "activity.is_critical": True,
                    "activity.duration_percent_complete": activity.get("duration_percent_complete"),
                },
                "evidence_contract": WORKSPACE_READ_CONTRACT,
            })

    category_rules = (
        ("field_issues", _OPEN_STATUSES, "open_field_issue", "field_issue_followup_candidate"),
        ("safety_observations", _OPEN_STATUSES, "open_safety_observation", "safety_followup_candidate"),
        ("equipment_status_reports", _EQUIPMENT_FAILURE_STATUSES, "equipment_unavailable", "equipment_followup_candidate"),
        ("quality_records", _QUALITY_FAILURE_STATUSES, "quality_record_followup", "quality_followup_candidate"),
        ("inspections", _QUALITY_FAILURE_STATUSES, "inspection_followup", "inspection_followup_candidate"),
        ("punch_items", _OPEN_STATUSES, "open_punch_item", "punch_followup_candidate"),
    )
    for collection_name, statuses, signal_type, classification in category_rules:
        raw_records = snapshot.get(collection_name, [])
        if not isinstance(raw_records, (list, tuple)):
            continue
        for record in raw_records:
            if not isinstance(record, Mapping):
                continue
            status = record.get("status")
            if not isinstance(status, str) or status.strip().casefold() not in statuses:
                continue
            if len(signals) >= 20:
                signals_truncated = True
                break
            evidence_id = _record_id(record)
            activity_id = record.get("activity_id")
            evidence: dict[str, object] = {
                "signal_type": signal_type,
                "classification": classification,
                "status": "needs_review",
                "project_revision": project_revision,
                "record_collection": collection_name,
                "record_id": evidence_id,
                "basis_fields": {"status": status.strip()},
                "evidence_contract": WORKSPACE_READ_CONTRACT,
            }
            if isinstance(activity_id, str) and activity_id.strip():
                evidence["activity_id"] = activity_id.strip()[:128]
                evidence["basis_fields"] = {
                    **evidence["basis_fields"],
                    "activity_id": activity_id.strip()[:128],
                }
            severity = record.get("severity")
            if isinstance(severity, str) and severity.strip():
                evidence["basis_fields"] = {
                    **evidence["basis_fields"],
                    "severity": severity.strip()[:80],
                }
            add(evidence)
        if len(signals) >= 20 and raw_records:
            signals_truncated = True

    counts: dict[str, int] = {}
    for signal in signals:
        signal_type = str(signal["signal_type"])
        counts[signal_type] = counts.get(signal_type, 0) + 1
    return signals, counts, signals_truncated


def _encode(value: Mapping[str, object]) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise AIProjectContextError("AI_PROJECT_CONTEXT_NOT_SERIALIZABLE") from exc


def build_assistant_project_context(
    snapshot: Mapping[str, object],
    *,
    tenant_id: str,
    project_id: str,
    project_revision: int,
) -> dict[str, object]:
    """Build an allowlisted project read context after strict contract and scope checks."""
    expected = (tenant_id, project_id, project_revision)
    if (
        not isinstance(tenant_id, str) or not tenant_id.strip()
        or not isinstance(project_id, str) or not project_id.strip()
        or isinstance(project_revision, bool)
        or not isinstance(project_revision, int)
        or project_revision < 0
    ):
        raise AIProjectContextError("AI_PROJECT_CONTEXT_SCOPE_INVALID")
    if snapshot.get("contract_version") != WORKSPACE_READ_CONTRACT:
        raise AIProjectContextError("AI_PROJECT_CONTEXT_READ_CONTRACT_UNSUPPORTED")
    if not _scope_matches(snapshot.get("context"), tenant_id=expected[0], project_id=expected[1], revision=expected[2]):
        raise AIProjectContextError("AI_PROJECT_CONTEXT_SCOPE_MISMATCH")

    workspace = snapshot.get("workspace")
    if not isinstance(workspace, Mapping) or workspace.get("contract_version") != WORKSPACE_CONTRACT:
        raise AIProjectContextError("AI_PROJECT_CONTEXT_WORKSPACE_CONTRACT_UNSUPPORTED")
    if not _scope_matches(workspace.get("context"), tenant_id=expected[0], project_id=expected[1], revision=expected[2]):
        raise AIProjectContextError("AI_PROJECT_CONTEXT_WORKSPACE_SCOPE_MISMATCH")

    all_rows = _activity_rows(workspace.get("activities"))
    schedule_available = [row for row in all_rows if row["schedule_facts_available"] is True]
    critical_known = [
        row for row in all_rows if isinstance(row.get("critical"), bool)
    ]
    collections: dict[str, list[dict[str, object]]] = {}
    record_counts: dict[str, int] = {}
    for key in _RECORD_COLLECTIONS:
        raw_records = snapshot.get(key, [])
        if not isinstance(raw_records, (list, tuple)):
            raise AIProjectContextError("AI_PROJECT_CONTEXT_RECORD_COLLECTION_INVALID")
        record_counts[key] = len(raw_records)
        if raw_records:
            rows = _record_rows(raw_records)
            if rows:
                collections[key] = rows

    truncated = len(all_rows) > MAX_ACTIVITY_ROWS or any(
        record_counts[key] > len(collections.get(key, [])) for key in record_counts
    )
    engineering_signals, signal_counts, signals_truncated = _engineering_signals(
        all_rows, snapshot, project_revision
    )
    context: dict[str, object] = {
        "contract_version": PROJECT_CONTEXT_CONTRACT,
        "availability": "available",
        "scope": {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "project_revision": project_revision,
        },
        "source": {
            "contract_version": WORKSPACE_READ_CONTRACT,
            "scope_revision": project_revision,
            "calculation_note": (
                "Schedule dates, float and criticality are included only when supplied "
                "by the workspace schedule-facts projection. This envelope does not expose "
                "a snapshot ID; do not invent one."
            ),
        },
        "activity_summary": {
            "total": len(all_rows),
            "with_schedule_facts": len(schedule_available),
            "without_complete_schedule_facts": len(all_rows) - len(schedule_available),
            "critical_flag_known_count": len(critical_known),
            "critical_true_count_among_known_flags": sum(
                row.get("critical") is True for row in critical_known
            ),
        },
        "activities": all_rows[:MAX_ACTIVITY_ROWS],
        "record_counts": record_counts,
        "records": collections,
        "engineering_signals": engineering_signals,
        "engineering_signal_counts": signal_counts,
        "signals_truncated": signals_truncated,
        "truncated": truncated or signals_truncated,
    }

    # Keep the model input bounded while retaining source counts and the highest
    # priority current activities. Drop auxiliary rows first, then activity rows.
    while len(_encode(context)) > MAX_CONTEXT_CHARS:
        if collections:
            last_key = next(reversed(collections))
            if collections[last_key]:
                collections[last_key].pop()
            if not collections[last_key]:
                del collections[last_key]
            context["records"] = collections
            context["truncated"] = True
            continue
        activities = context["activities"]
        if isinstance(activities, list) and len(activities) > 1:
            activities.pop()
            context["truncated"] = True
            continue
        raise AIProjectContextError("AI_PROJECT_CONTEXT_SIZE_LIMIT")
    if len(all_rows) > MAX_ACTIVITY_ROWS:
        context["truncated"] = True
    return context


def unavailable_assistant_project_context(
    *, tenant_id: str, project_id: str, project_revision: int, reason_code: str
) -> dict[str, object]:
    """Return a compact, explicit non-availability state without faking project facts."""
    safe_reason = reason_code if reason_code in {
        "WORKSPACE_READ_NOT_CONFIGURED",
        "WORKSPACE_READ_NOT_FOUND",
        "WORKSPACE_READ_UNAVAILABLE",
    } else "WORKSPACE_READ_UNAVAILABLE"
    return {
        "contract_version": PROJECT_CONTEXT_CONTRACT,
        "availability": "unavailable",
        "scope": {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "project_revision": project_revision,
        },
        "reason_code": safe_reason,
        "activities": [],
        "records": {},
        "truncated": False,
    }
