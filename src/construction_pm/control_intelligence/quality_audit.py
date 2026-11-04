from __future__ import annotations

"""Deterministic, read-only first-pass schedule quality audit.

The audit consumes the same immutable canonical schedule snapshot as the
Shared Scheduling Core. It does not calculate dates, float, criticality, costs
or resource demand. Those values remain owned by the Shared Core.
"""

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from typing import Mapping, Sequence


_ENGINE_VERSION = "eng06-schedule-quality-audit.v1"
_VALID_RELATIONSHIP_TYPES = frozenset({"FS", "SS", "FF", "SF"})


def _as_records(value: object, field_name: str) -> list[dict[str, object]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(f"INVALID_SCHEDULE_AUDIT_INPUT:{field_name}")
    return value


def _iso_date(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _iso_datetime(value: object) -> date | datetime | None:
    if not isinstance(value, str) or not value:
        return None
    if "T" in value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return _iso_date(value)


def _lag_number(value: object, mode: str) -> Decimal | None:
    if mode == "DATE_BASED":
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        return Decimal(value)
    if mode == "TIME_AWARE":
        if not isinstance(value, dict):
            return None
        if not isinstance(value.get("unit"), str) or not value.get("unit"):
            return None
        try:
            parsed = Decimal(str(value.get("value")))
        except Exception:
            return None
        return parsed if parsed.is_finite() else None
    return None


def _cycle_components(
    activity_ids: set[str],
    adjacency: Mapping[str, set[str]],
) -> list[tuple[str, ...]]:
    """Return cyclic strongly connected components with iterative Kosaraju DFS."""
    reverse: dict[str, set[str]] = defaultdict(set)
    for predecessor, successors in adjacency.items():
        for successor in successors:
            if predecessor in activity_ids and successor in activity_ids:
                reverse[successor].add(predecessor)

    visited: set[str] = set()
    finish_order: list[str] = []
    for start in sorted(activity_ids):
        if start in visited:
            continue
        visited.add(start)
        pending = [(start, iter(sorted(adjacency.get(start, set()))))]
        while pending:
            node, successors = pending[-1]
            try:
                successor = next(successors)
            except StopIteration:
                pending.pop()
                finish_order.append(node)
                continue
            if successor in activity_ids and successor not in visited:
                visited.add(successor)
                pending.append((successor, iter(sorted(adjacency.get(successor, set())))))

    visited.clear()
    components: list[tuple[str, ...]] = []
    for start in reversed(finish_order):
        if start in visited:
            continue
        component: list[str] = []
        pending_nodes = [start]
        visited.add(start)
        while pending_nodes:
            node = pending_nodes.pop()
            component.append(node)
            for predecessor in reverse.get(node, set()):
                if predecessor not in visited:
                    visited.add(predecessor)
                    pending_nodes.append(predecessor)
        self_loop = len(component) == 1 and component[0] in adjacency.get(component[0], set())
        if len(component) > 1 or self_loop:
            components.append(tuple(sorted(component)))
    return sorted(components)


def _context_records(
    audit_context: Mapping[str, object] | None,
    key: str,
) -> list[dict[str, object]] | None:
    if audit_context is None or key not in audit_context or audit_context[key] is None:
        return None
    return _as_records(audit_context[key], key)


def _audit_wbs_registry(
    audit_context: Mapping[str, object] | None,
    activities: Mapping[str, dict[str, object]],
    add,
    *,
    mode: str,
) -> tuple[str, int]:
    nodes = _context_records(audit_context, "wbs_nodes")
    if nodes is None:
        return "not_evaluated_wbs_repository_not_configured", 0

    node_by_id: dict[str, dict[str, object]] = {}
    sibling_codes: set[tuple[str, str, str]] = set()
    adjacency: dict[str, set[str]] = defaultdict(set)
    roots = 0

    for node in nodes:
        wbs_id = node.get("wbs_id")
        if not isinstance(wbs_id, str) or not wbs_id.strip():
            add("INVALID_WBS_ID", "critical", "quality.finding.invalid_wbs_id", object_type="wbs")
            continue
        if wbs_id in node_by_id:
            add("DUPLICATE_WBS_ID", "critical", "quality.finding.duplicate_wbs_id", object_type="wbs", object_id=wbs_id)
            continue
        node_by_id[wbs_id] = node
        parent_kind = node.get("parent_kind")
        parent_id = node.get("parent_wbs_id")
        code = node.get("code")
        if not isinstance(code, str) or not code.strip():
            add("INVALID_WBS_CODE", "critical", "quality.finding.invalid_wbs_code", object_type="wbs", object_id=wbs_id)
        if parent_kind == "project":
            roots += 1
            if parent_id is not None:
                add("INVALID_WBS_ROOT_PARENT", "critical", "quality.finding.invalid_wbs_root_parent", object_type="wbs", object_id=wbs_id)
        elif parent_kind == "wbs":
            if not isinstance(parent_id, str) or not parent_id:
                add("WBS_PARENT_MISSING", "critical", "quality.finding.wbs_parent_missing", object_type="wbs", object_id=wbs_id)
            else:
                adjacency[parent_id].add(wbs_id)
        else:
            add("INVALID_WBS_PARENT_KIND", "critical", "quality.finding.invalid_wbs_parent_kind", object_type="wbs", object_id=wbs_id)
        if isinstance(code, str) and code.strip():
            code_key = (str(parent_kind), str(parent_id or ""), code)
            if code_key in sibling_codes:
                add("DUPLICATE_WBS_SIBLING_CODE", "critical", "quality.finding.duplicate_wbs_sibling_code", object_type="wbs", object_id=wbs_id)
            sibling_codes.add(code_key)

    if not nodes or roots != 1:
        add(
            "PROJECT_WBS_ROOT_COUNT_INVALID",
            "critical",
            "quality.finding.project_wbs_root_count_invalid",
            evidence={"root_count": roots, "node_count": len(nodes)},
        )

    for wbs_id, node in node_by_id.items():
        if node.get("parent_kind") == "wbs":
            parent_id = node.get("parent_wbs_id")
            if isinstance(parent_id, str) and parent_id not in node_by_id:
                add(
                    "DANGLING_WBS_PARENT",
                    "critical",
                    "quality.finding.dangling_wbs_parent",
                    object_type="wbs",
                    object_id=wbs_id,
                    related_ids=(parent_id,),
                )
    for component in _cycle_components(set(node_by_id), adjacency):
        add(
            "WBS_HIERARCHY_CYCLE",
            "critical",
            "quality.finding.wbs_hierarchy_cycle",
            object_type="wbs_hierarchy",
            object_id=component[0],
            related_ids=component,
        )

    expected_ancestry: dict[str, list[str] | None] = {}
    for wbs_id, node in node_by_id.items():
        parent = node.get("parent_wbs_id")
        ancestors: list[str] = []
        visited: set[str] = set()
        valid = True
        while isinstance(parent, str):
            if parent in visited or parent not in node_by_id:
                valid = False
                break
            visited.add(parent)
            ancestors.append(parent)
            parent_node = node_by_id[parent]
            if parent_node.get("parent_kind") != "wbs":
                break
            parent = parent_node.get("parent_wbs_id")
        expected_ancestry[wbs_id] = list(reversed(ancestors)) if valid else None

    for activity_id, activity in sorted(activities.items()):
        if mode == "TIME_AWARE":
            break
        if activity.get("status_code") == "Inactive" or activity.get("activity_type") == "WBS Summary":
            continue
        wbs_id = activity.get("wbs_id")
        if not isinstance(wbs_id, str) or not wbs_id:
            add(
                "ACTIVITY_MISSING_WBS_ASSIGNMENT",
                "warning",
                "quality.finding.activity_missing_wbs_assignment",
                object_type="activity",
                object_id=activity_id,
            )
            continue
        if wbs_id not in node_by_id:
            add(
                "ACTIVITY_WBS_NOT_FOUND",
                "critical",
                "quality.finding.activity_wbs_not_found",
                object_type="activity",
                object_id=activity_id,
                related_ids=(wbs_id,),
            )
            continue
        actual_ancestry = activity.get("wbs_ancestry", [])
        expected = expected_ancestry.get(wbs_id)
        if expected is not None and actual_ancestry != expected:
            add(
                "ACTIVITY_WBS_ANCESTRY_MISMATCH",
                "warning",
                "quality.finding.activity_wbs_ancestry_mismatch",
                object_type="activity",
                object_id=activity_id,
                related_ids=(wbs_id,),
                evidence={"expected_ancestry": expected, "snapshot_ancestry": actual_ancestry},
            )
    return (
        "evaluated_registry_only_activity_assignment_not_in_time_aware_snapshot"
        if mode == "TIME_AWARE"
        else "evaluated"
    ), len(nodes)


def _audit_baselines(
    audit_context: Mapping[str, object] | None,
    activities: Mapping[str, dict[str, object]],
    wbs_nodes: list[dict[str, object]] | None,
    add,
    *,
    current_revision: object,
) -> tuple[str, int, int]:
    baselines = _context_records(audit_context, "baselines")
    rows = _context_records(audit_context, "baseline_activities")
    assignments = _context_records(audit_context, "baseline_assignments")
    if baselines is None:
        return "not_evaluated_baseline_repository_not_configured", 0, 0

    by_id: dict[str, dict[str, object]] = {}
    for baseline in baselines:
        baseline_id = baseline.get("baseline_id")
        if not isinstance(baseline_id, str) or not baseline_id.strip():
            add("INVALID_BASELINE_ID", "critical", "quality.finding.invalid_baseline_id", object_type="baseline")
            continue
        if baseline_id in by_id:
            add("DUPLICATE_BASELINE_ID", "critical", "quality.finding.duplicate_baseline_id", object_type="baseline", object_id=baseline_id)
            continue
        by_id[baseline_id] = baseline
        source_revision = baseline.get("source_revision")
        if isinstance(source_revision, int) and isinstance(current_revision, int) and source_revision > current_revision:
            add(
                "BASELINE_SOURCE_REVISION_IN_FUTURE",
                "critical",
                "quality.finding.baseline_source_revision_in_future",
                object_type="baseline",
                object_id=baseline_id,
                evidence={"source_revision": source_revision, "current_revision": current_revision},
            )

    if assignments is not None:
        roles: set[str] = set()
        for assignment in assignments:
            role = assignment.get("role")
            baseline_id = assignment.get("baseline_id")
            if not isinstance(role, str) or not role:
                add("INVALID_BASELINE_ROLE_ASSIGNMENT", "critical", "quality.finding.invalid_baseline_role_assignment", object_type="baseline_role")
                continue
            if role in roles:
                add("DUPLICATE_BASELINE_ROLE_ASSIGNMENT", "critical", "quality.finding.duplicate_baseline_role_assignment", object_type="baseline_role", object_id=role)
            roles.add(role)
            if not isinstance(baseline_id, str) or baseline_id not in by_id:
                add(
                    "BASELINE_ROLE_TARGET_MISSING",
                    "critical",
                    "quality.finding.baseline_role_target_missing",
                    object_type="baseline_role",
                    object_id=role,
                    related_ids=(baseline_id,) if isinstance(baseline_id, str) else (),
                )

    if rows is None:
        return "partial_baseline_metadata_only", len(by_id), 0

    seen: set[tuple[str, str]] = set()
    current_wbs_ids = (
        {str(node["wbs_id"]) for node in wbs_nodes if isinstance(node.get("wbs_id"), str)}
        if wbs_nodes is not None
        else None
    )
    row_count = 0
    rows_by_baseline: dict[str, int] = defaultdict(int)
    for row in rows:
        baseline_id = row.get("baseline_id")
        activity_id = row.get("activity_id")
        if not isinstance(baseline_id, str) or baseline_id not in by_id:
            add(
                "BASELINE_ACTIVITY_PARENT_MISSING",
                "critical",
                "quality.finding.baseline_activity_parent_missing",
                object_type="baseline_activity",
                object_id=activity_id if isinstance(activity_id, str) else None,
                related_ids=(baseline_id,) if isinstance(baseline_id, str) else (),
            )
            continue
        if not isinstance(activity_id, str) or not activity_id:
            add("INVALID_BASELINE_ACTIVITY_ID", "critical", "quality.finding.invalid_baseline_activity_id", object_type="baseline_activity", related_ids=(baseline_id,))
            continue
        key = (baseline_id, activity_id)
        if key in seen:
            add(
                "DUPLICATE_BASELINE_ACTIVITY",
                "critical",
                "quality.finding.duplicate_baseline_activity",
                object_type="baseline_activity",
                object_id=activity_id,
                related_ids=(baseline_id,),
            )
            continue
        seen.add(key)
        row_count += 1
        rows_by_baseline[baseline_id] += 1
        start = _iso_date(row.get("planned_start"))
        finish = _iso_date(row.get("planned_finish"))
        if start is None or finish is None or finish < start:
            add(
                "INVALID_BASELINE_ACTIVITY_WINDOW",
                "critical",
                "quality.finding.invalid_baseline_activity_window",
                object_type="baseline_activity",
                object_id=activity_id,
                related_ids=(baseline_id,),
                evidence={"planned_start": row.get("planned_start"), "planned_finish": row.get("planned_finish")},
            )
        if activity_id not in activities:
            add(
                "BASELINE_ACTIVITY_ABSENT_FROM_CURRENT_SCHEDULE",
                "info",
                "quality.finding.baseline_activity_absent_from_current_schedule",
                object_type="baseline_activity",
                object_id=activity_id,
                related_ids=(baseline_id,),
            )
        wbs_id = row.get("wbs_id")
        if wbs_id is not None and current_wbs_ids is not None and wbs_id not in current_wbs_ids:
            add(
                "BASELINE_WBS_ABSENT_FROM_CURRENT_REGISTRY",
                "info",
                "quality.finding.baseline_wbs_absent_from_current_registry",
                object_type="baseline_activity",
                object_id=activity_id,
                related_ids=(baseline_id, str(wbs_id)),
            )
    for baseline_id in by_id:
        if rows_by_baseline[baseline_id] == 0:
            add(
                "BASELINE_HAS_NO_ACTIVITY_ROWS",
                "warning",
                "quality.finding.baseline_has_no_activity_rows",
                object_type="baseline",
                object_id=baseline_id,
            )
    if not by_id:
        return "evaluated_no_baselines", 0, 0
    return "evaluated", len(by_id), row_count


def _decimal_value(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        result = Decimal(str(value))
    except Exception:
        return None
    return result if result.is_finite() else None


def _audit_resources(
    audit_context: Mapping[str, object] | None,
    activities: Mapping[str, dict[str, object]],
    add,
) -> tuple[str, int, int]:
    assignments = _context_records(audit_context, "resource_assignments")
    periods = _context_records(audit_context, "resource_periods")
    if assignments is None:
        return "not_evaluated_resource_assignment_repository_not_configured", 0, 0

    by_id: dict[str, dict[str, object]] = {}
    by_activity: dict[str, list[dict[str, object]]] = defaultdict(list)
    for assignment in assignments:
        assignment_id = assignment.get("assignment_id")
        activity_id = assignment.get("activity_id")
        resource_id = assignment.get("resource_id")
        if not isinstance(assignment_id, str) or not assignment_id:
            add("INVALID_RESOURCE_ASSIGNMENT_ID", "critical", "quality.finding.invalid_resource_assignment_id", object_type="resource_assignment")
            continue
        if assignment_id in by_id:
            add("DUPLICATE_RESOURCE_ASSIGNMENT_ID", "critical", "quality.finding.duplicate_resource_assignment_id", object_type="resource_assignment", object_id=assignment_id)
            continue
        by_id[assignment_id] = assignment
        if not isinstance(activity_id, str) or activity_id not in activities:
            add(
                "RESOURCE_ASSIGNMENT_ACTIVITY_NOT_FOUND",
                "critical",
                "quality.finding.resource_assignment_activity_not_found",
                object_type="resource_assignment",
                object_id=assignment_id,
                related_ids=(activity_id,) if isinstance(activity_id, str) else (),
            )
        else:
            by_activity[activity_id].append(assignment)
        if not isinstance(resource_id, str) or not resource_id:
            add("INVALID_RESOURCE_ASSIGNMENT_RESOURCE", "critical", "quality.finding.invalid_resource_assignment_resource", object_type="resource_assignment", object_id=assignment_id)

        quantities = ("units", "actual_units", "remaining_units")
        if any(assignment.get(field) is not None for field in quantities):
            if not isinstance(assignment.get("unit"), str) or not assignment.get("unit"):
                add(
                    "RESOURCE_ASSIGNMENT_UNIT_MISSING",
                    "warning",
                    "quality.finding.resource_assignment_unit_missing",
                    object_type="resource_assignment",
                    object_id=assignment_id,
                )
        costs = ("planned_cost", "actual_cost", "remaining_cost")
        if any(assignment.get(field) is not None for field in costs):
            if not isinstance(assignment.get("currency"), str) or not assignment.get("currency"):
                add(
                    "RESOURCE_ASSIGNMENT_CURRENCY_MISSING",
                    "warning",
                    "quality.finding.resource_assignment_currency_missing",
                    object_type="resource_assignment",
                    object_id=assignment_id,
                )
        for field in (*quantities, *costs, "units_per_time", "hours_per_units_time_period"):
            if assignment.get(field) is not None and _decimal_value(assignment.get(field)) is None:
                add(
                    "INVALID_RESOURCE_ASSIGNMENT_NUMERIC_VALUE",
                    "critical",
                    "quality.finding.invalid_resource_assignment_numeric_value",
                    object_type="resource_assignment",
                    object_id=assignment_id,
                    evidence={"field": field, "value": assignment.get(field)},
                )

    for activity_id, activity in sorted(activities.items()):
        if activity.get("activity_type") != "Resource Dependent" or activity.get("status_code") == "Inactive":
            continue
        linked = by_activity.get(activity_id, [])
        if not linked:
            add(
                "RESOURCE_DEPENDENT_ACTIVITY_WITHOUT_ASSIGNMENT",
                "critical",
                "quality.finding.resource_dependent_activity_without_assignment",
                object_type="activity",
                object_id=activity_id,
            )
            continue
        unresolved = [row for row in linked if row.get("is_driving") is None]
        if unresolved:
            add(
                "RESOURCE_DEPENDENT_DRIVING_ROLE_UNRESOLVED",
                "warning",
                "quality.finding.resource_dependent_driving_role_unresolved",
                object_type="activity",
                object_id=activity_id,
                related_ids=[str(row["assignment_id"]) for row in unresolved if isinstance(row.get("assignment_id"), str)],
            )
        else:
            driving = [row for row in linked if row.get("is_driving") is True]
            if len(driving) != 1:
                add(
                    "RESOURCE_DEPENDENT_DRIVING_ASSIGNMENT_COUNT_INVALID",
                    "critical",
                    "quality.finding.resource_dependent_driving_assignment_count_invalid",
                    object_type="activity",
                    object_id=activity_id,
                    evidence={"driving_assignment_count": len(driving)},
                )

    if periods is None:
        return "partial_resource_assignments_only", len(by_id), 0

    seen_periods: set[tuple[str, str]] = set()
    for period in periods:
        assignment_id = period.get("assignment_id")
        period_start = period.get("period_start")
        if not isinstance(assignment_id, str) or assignment_id not in by_id:
            add(
                "RESOURCE_PERIOD_ASSIGNMENT_NOT_FOUND",
                "critical",
                "quality.finding.resource_period_assignment_not_found",
                object_type="resource_period",
                object_id=period_start if isinstance(period_start, str) else None,
                related_ids=(assignment_id,) if isinstance(assignment_id, str) else (),
            )
            continue
        assignment = by_id[assignment_id]
        key = (assignment_id, str(period_start))
        if key in seen_periods:
            add(
                "DUPLICATE_RESOURCE_ASSIGNMENT_PERIOD",
                "critical",
                "quality.finding.duplicate_resource_assignment_period",
                object_type="resource_period",
                object_id=assignment_id,
                evidence={"period_start": period_start},
            )
        seen_periods.add(key)
        if period.get("activity_id") != assignment.get("activity_id") or period.get("resource_id") != assignment.get("resource_id"):
            add(
                "RESOURCE_PERIOD_PARENT_MISMATCH",
                "critical",
                "quality.finding.resource_period_parent_mismatch",
                object_type="resource_period",
                object_id=assignment_id,
                evidence={
                    "period_activity_id": period.get("activity_id"),
                    "assignment_activity_id": assignment.get("activity_id"),
                    "period_resource_id": period.get("resource_id"),
                    "assignment_resource_id": assignment.get("resource_id"),
                },
            )
        if _iso_date(period_start) is None:
            add(
                "INVALID_RESOURCE_PERIOD_START",
                "critical",
                "quality.finding.invalid_resource_period_start",
                object_type="resource_period",
                object_id=assignment_id,
                evidence={"period_start": period_start},
            )
        for field in ("units", "cost"):
            if period.get(field) is not None and _decimal_value(period.get(field)) is None:
                add(
                    "INVALID_RESOURCE_PERIOD_VALUE",
                    "critical",
                    "quality.finding.invalid_resource_period_value",
                    object_type="resource_period",
                    object_id=assignment_id,
                    evidence={"field": field, "value": period.get(field)},
                )
    return "evaluated_referential_integrity", len(by_id), len(periods)


def build_schedule_quality_audit(
    canonical_payload: str,
    *,
    core_diagnostics: Sequence[Mapping[str, object]] = (),
    evaluation_status: str = "completed",
    audit_context: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build a revision-bound audit report without modifying the project.

    canonical_payload must be the persisted immutable snapshot content.
    Schedule-derived findings are passed through from Shared Core diagnostics;
    this function never runs a second scheduler.
    """
    try:
        payload = json.loads(canonical_payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("INVALID_SCHEDULE_AUDIT_SNAPSHOT") from exc
    if not isinstance(payload, dict):
        raise ValueError("INVALID_SCHEDULE_AUDIT_SNAPSHOT")

    activities = _as_records(payload.get("activities"), "activities")
    relationships = _as_records(payload.get("relationships"), "relationships")
    constraints = _as_records(payload.get("constraints", []), "constraints")
    calendar_assignments = _as_records(
        payload.get("activity_calendar_assignments", []),
        "activity_calendar_assignments",
    )
    schedule_options = payload.get("schedule_options", {})
    if not isinstance(schedule_options, dict):
        raise ValueError("INVALID_SCHEDULE_AUDIT_INPUT:schedule_options")

    findings: list[dict[str, object]] = []
    seen_findings: set[tuple[str, str, tuple[str, ...]]] = set()

    def add(
        rule_id: str,
        severity: str,
        message_key: str,
        *,
        object_type: str = "project",
        object_id: str | None = None,
        related_ids: Sequence[str] = (),
        evidence: Mapping[str, object] | None = None,
    ) -> None:
        normalized_related = tuple(sorted(str(item) for item in related_ids))
        key = (rule_id, object_id or "", normalized_related)
        if key in seen_findings:
            return
        seen_findings.add(key)
        finding: dict[str, object] = {
            "finding_id": f"{rule_id}:{object_id or 'project'}:{','.join(normalized_related)}",
            "rule_id": rule_id,
            "severity": severity,
            "message_key": message_key,
            "object_type": object_type,
            "object_id": object_id,
            "related_object_ids": list(normalized_related),
            "evidence": dict(evidence or {}),
        }
        findings.append(finding)

    activity_ids: set[str] = set()
    activity_rows: dict[str, dict[str, object]] = {}
    for activity in activities:
        activity_id = activity.get("id")
        if not isinstance(activity_id, str) or not activity_id.strip():
            add(
                "INVALID_ACTIVITY_ID",
                "critical",
                "quality.finding.invalid_activity_id",
                object_type="activity",
            )
            continue
        if activity_id in activity_ids:
            add(
                "DUPLICATE_ACTIVITY_ID",
                "critical",
                "quality.finding.duplicate_activity_id",
                object_type="activity",
                object_id=activity_id,
            )
        activity_ids.add(activity_id)
        activity_rows.setdefault(activity_id, activity)

    predecessor_count: dict[str, int] = defaultdict(int)
    successor_count: dict[str, int] = defaultdict(int)
    adjacency: dict[str, set[str]] = defaultdict(set)
    valid_edges: list[dict[str, object]] = []
    seen_edges: set[tuple[str, str, str, int]] = set()
    lead_count = 0
    positive_lag_count = 0
    invalid_relationship_count = 0

    for index, relationship in enumerate(relationships):
        predecessor = relationship.get("predecessor_id")
        successor = relationship.get("successor_id")
        relationship_type = relationship.get("type", "FS")
        lag = relationship.get("lag", 0)
        lag_number = _lag_number(lag, str(payload.get("mode")))
        evidence = {
            "relationship_index": index,
            "relationship_type": relationship_type,
            "lag": lag,
        }
        if (
            not isinstance(predecessor, str)
            or not predecessor
            or not isinstance(successor, str)
            or not successor
            or predecessor == successor
            or predecessor not in activity_ids
            or successor not in activity_ids
            or not isinstance(relationship_type, str)
            or relationship_type not in _VALID_RELATIONSHIP_TYPES
            or lag_number is None
        ):
            invalid_relationship_count += 1
            related = [
                item for item in (predecessor, successor)
                if isinstance(item, str) and item
            ]
            add(
                "INVALID_OR_DANGLING_RELATIONSHIP",
                "critical",
                "quality.finding.invalid_or_dangling_relationship",
                object_type="relationship",
                related_ids=related,
                evidence=evidence,
            )
            continue

        edge_key = (predecessor, successor, relationship_type, str(lag_number))
        if edge_key in seen_edges:
            add(
                "DUPLICATE_RELATIONSHIP",
                "warning",
                "quality.finding.duplicate_relationship",
                object_type="relationship",
                related_ids=(predecessor, successor),
                evidence=evidence,
            )
            continue
        seen_edges.add(edge_key)
        valid_edges.append(relationship)
        predecessor_count[successor] += 1
        successor_count[predecessor] += 1
        adjacency[predecessor].add(successor)

        if lag_number < 0:
            lead_count += 1
            add(
                "RELATIONSHIP_LEAD_PRESENT",
                "warning",
                "quality.finding.relationship_lead_present",
                object_type="relationship",
                related_ids=(predecessor, successor),
                evidence=evidence,
            )
        elif lag_number > 0:
            positive_lag_count += 1

    for component in _cycle_components(activity_ids, adjacency):
        add(
            "NETWORK_CYCLE",
            "critical",
            "quality.finding.network_cycle",
            object_type="activity_network",
            object_id=component[0],
            related_ids=component,
        )

    open_predecessors = 0
    open_successors = 0
    for activity_id, activity in sorted(activity_rows.items()):
        activity_type = activity.get("activity_type")
        if activity.get("status_code") == "Inactive":
            continue
        if predecessor_count[activity_id] == 0 and activity_type not in {
            "Start Milestone",
            "WBS Summary",
        }:
            open_predecessors += 1
            add(
                "OPEN_PREDECESSOR",
                "warning",
                "quality.finding.open_predecessor",
                object_type="activity",
                object_id=activity_id,
            )
        if successor_count[activity_id] == 0 and activity_type not in {
            "Finish Milestone",
            "WBS Summary",
        }:
            open_successors += 1
            add(
                "OPEN_SUCCESSOR",
                "warning",
                "quality.finding.open_successor",
                object_type="activity",
                object_id=activity_id,
            )

    constraint_count_by_activity: dict[str, int] = defaultdict(int)
    seen_constraints: set[tuple[str, str, str]] = set()
    duplicate_constraint_count = 0
    invalid_constraint_reference_count = 0
    for constraint in constraints:
        activity_id = constraint.get("activity_id")
        constraint_type = constraint.get("type")
        constraint_date = constraint.get("date")
        if not isinstance(activity_id, str) or not activity_id:
            add(
                "INVALID_ACTIVITY_CONSTRAINT",
                "critical",
                "quality.finding.invalid_activity_constraint",
                object_type="constraint",
            )
            invalid_constraint_reference_count += 1
            continue
        if activity_id not in activity_ids:
            add(
                "CONSTRAINT_ACTIVITY_NOT_FOUND",
                "critical",
                "quality.finding.constraint_activity_not_found",
                object_type="constraint",
                object_id=activity_id,
            )
            invalid_constraint_reference_count += 1
        constraint_count_by_activity[activity_id] += 1
        key = (activity_id, str(constraint_type), str(constraint_date))
        if key in seen_constraints:
            duplicate_constraint_count += 1
            add(
                "DUPLICATE_ACTIVITY_CONSTRAINT",
                "warning",
                "quality.finding.duplicate_activity_constraint",
                object_type="constraint",
                object_id=activity_id,
                evidence={"type": constraint_type, "date": constraint_date},
            )
        seen_constraints.add(key)

    assigned_activity_ids: set[str] = set()
    for assignment in calendar_assignments:
        activity_id = assignment.get("activity_id")
        if not isinstance(activity_id, str) or not activity_id:
            add(
                "INVALID_ACTIVITY_CALENDAR_ASSIGNMENT",
                "critical",
                "quality.finding.invalid_activity_calendar_assignment",
                object_type="calendar_assignment",
            )
            continue
        if activity_id not in activity_ids:
            add(
                "DANGLING_ACTIVITY_CALENDAR_ASSIGNMENT",
                "critical",
                "quality.finding.dangling_activity_calendar_assignment",
                object_type="calendar_assignment",
                object_id=activity_id,
            )
        if activity_id in assigned_activity_ids:
            add(
                "DUPLICATE_ACTIVITY_CALENDAR_ASSIGNMENT",
                "warning",
                "quality.finding.duplicate_activity_calendar_assignment",
                object_type="activity",
                object_id=activity_id,
            )
        assigned_activity_ids.add(activity_id)

    date_based = payload.get("mode") == "DATE_BASED"
    data_date = (
        _iso_date(schedule_options.get("data_date"))
        if date_based
        else _iso_datetime(schedule_options.get("data_date"))
    )
    actual_after_data_date = 0
    if data_date is not None:
        for activity_id, activity in sorted(activity_rows.items()):
            fields = ("actual_start", "actual_finish") if date_based else ("actual_start",)
            for field_name in fields:
                actual_value = (
                    _iso_date(activity.get(field_name))
                    if date_based
                    else _iso_datetime(activity.get(field_name))
                )
                if (
                    actual_value is not None
                    and type(actual_value) is type(data_date)
                    and actual_value > data_date
                ):
                    actual_after_data_date += 1
                    add(
                        "ACTUAL_AFTER_DATA_DATE",
                        "warning",
                        "quality.finding.actual_after_data_date",
                        object_type="activity",
                        object_id=activity_id,
                        evidence={
                            "field": field_name,
                            "actual_date": actual_value.isoformat(),
                            "data_date": data_date.isoformat(),
                        },
                    )

    progress_consistency_count = 0
    for activity_id, activity in sorted(activity_rows.items()):
        actual_start = (
            _iso_date(activity.get("actual_start"))
            if date_based
            else _iso_datetime(activity.get("actual_start"))
        )
        actual_finish = (
            _iso_date(activity.get("actual_finish"))
            if date_based
            else _iso_datetime(activity.get("actual_finish"))
        )
        status = activity.get("status")
        progress_problem: str | None = None
        if (
            date_based
            and actual_start is not None
            and actual_finish is not None
            and actual_finish < actual_start
        ):
            progress_problem = "ACTUAL_FINISH_BEFORE_ACTUAL_START"
        elif status == "Completed" and actual_finish is None:
            progress_problem = "COMPLETED_ACTIVITY_MISSING_ACTUAL_FINISH"
        elif status == "In Progress" and actual_start is None:
            progress_problem = "IN_PROGRESS_ACTIVITY_MISSING_ACTUAL_START"
        elif status == "Not Started" and (actual_start is not None or actual_finish is not None):
            progress_problem = "NOT_STARTED_ACTIVITY_HAS_ACTUAL_DATES"
        if progress_problem is not None:
            progress_consistency_count += 1
            add(
                progress_problem,
                "critical" if progress_problem == "ACTUAL_FINISH_BEFORE_ACTUAL_START" else "warning",
                f"quality.finding.{progress_problem.lower()}",
                object_type="activity",
                object_id=activity_id,
                evidence={
                    "status": status,
                    "actual_start": None if actual_start is None else actual_start.isoformat(),
                    "actual_finish": None if actual_finish is None else actual_finish.isoformat(),
                },
            )

    out_of_sequence_candidates = 0
    for relationship in valid_edges:
        lag_number = _lag_number(
            relationship.get("lag", 0), str(payload.get("mode"))
        )
        if lag_number != 0:
            continue
        predecessor = str(relationship["predecessor_id"])
        successor = str(relationship["successor_id"])
        predecessor_activity = activity_rows[predecessor]
        successor_activity = activity_rows[successor]
        relationship_type = str(relationship.get("type", "FS"))

        if date_based:
            predecessor_start = _iso_date(predecessor_activity.get("actual_start"))
            predecessor_finish = _iso_date(predecessor_activity.get("actual_finish"))
            successor_start = _iso_date(successor_activity.get("actual_start"))
            successor_finish = _iso_date(successor_activity.get("actual_finish"))
            if relationship_type == "FS":
                left_event, right_event = predecessor_finish, successor_start
            elif relationship_type == "SS":
                left_event, right_event = predecessor_start, successor_start
            elif relationship_type == "FF":
                left_event, right_event = predecessor_finish, successor_finish
            else:
                left_event, right_event = predecessor_start, successor_finish
            rule_scope = "DATE_BASED_ZERO_LAG_ALL_RELATIONSHIP_TYPES"
        elif relationship_type == "SS":
            left_event = _iso_datetime(predecessor_activity.get("actual_start"))
            right_event = _iso_datetime(successor_activity.get("actual_start"))
            rule_scope = "TIME_AWARE_ZERO_LAG_SS_ACTUAL_START_ONLY"
        else:
            # TIME_AWARE snapshots carry Actual Start but not Actual Finish.
            # Do not fabricate finish-event evidence for FS/FF/SF relationships.
            continue

        if (
            left_event is not None
            and right_event is not None
            and type(left_event) is type(right_event)
            and right_event < left_event
        ):
            out_of_sequence_candidates += 1
            add(
                "OUT_OF_SEQUENCE_PROGRESS_CANDIDATE",
                "warning",
                "quality.finding.out_of_sequence_progress_candidate",
                object_type="relationship",
                related_ids=(predecessor, successor),
                evidence={
                    "relationship_type": relationship_type,
                    "lag": 0,
                    "predecessor_event_date": left_event.isoformat(),
                    "successor_event_date": right_event.isoformat(),
                    "configured_oos_mode": schedule_options.get(
                        "out_of_sequence_schedule_type"
                    ),
                    "rule_scope": rule_scope,
                },
            )

    for diagnostic in core_diagnostics:
        if not isinstance(diagnostic, Mapping):
            continue
        code = diagnostic.get("code")
        activity_id = diagnostic.get("activity_id")
        if not isinstance(code, str) or not code:
            continue
        severity = "warning" if code == "NEGATIVE_FLOAT" else "critical"
        related = [
            value for value in (
                diagnostic.get("predecessor_id"),
                diagnostic.get("successor_id"),
            )
            if isinstance(value, str) and value
        ]
        add(
            f"CORE_{code}",
            severity,
            f"quality.finding.core.{code.lower()}",
            object_type="activity" if isinstance(activity_id, str) else "project",
            object_id=activity_id if isinstance(activity_id, str) else None,
            related_ids=related,
            evidence={
                key: diagnostic.get(key)
                for key in (
                    "code",
                    "severity",
                    "predecessor_id",
                    "successor_id",
                )
                if key in diagnostic
            },
        )

    wbs_coverage, wbs_node_count = _audit_wbs_registry(
        audit_context, activity_rows, add, mode=str(payload.get("mode"))
    )
    wbs_nodes = _context_records(audit_context, "wbs_nodes")
    baseline_coverage, baseline_count, baseline_activity_count = _audit_baselines(
        audit_context,
        activity_rows,
        wbs_nodes,
        add,
        current_revision=payload.get("project_revision"),
    )
    resource_coverage, resource_assignment_count, resource_period_count = _audit_resources(
        audit_context, activity_rows, add
    )

    findings.sort(
        key=lambda item: (
            {"critical": 0, "warning": 1, "info": 2}.get(str(item["severity"]), 3),
            str(item["rule_id"]),
            str(item["object_id"] or ""),
            str(item["finding_id"]),
        )
    )
    severity_counts = {
        level: sum(1 for item in findings if item["severity"] == level)
        for level in ("critical", "warning", "info")
    }

    data_date_status = (
        "evaluated"
        if data_date is not None
        else "not_applicable_no_time_aware_data_date"
        if payload.get("mode") == "TIME_AWARE"
        else "not_evaluated_no_data_date"
    )
    coverage = {
        "open_ends": "evaluated",
        "relationship_integrity": "evaluated",
        "network_cycles": "evaluated",
        "negative_float_and_core_diagnostics": (
            "evaluated"
            if payload.get("mode") == "DATE_BASED"
            and (evaluation_status == "completed" or core_diagnostics)
            else "not_applicable_time_aware"
            if payload.get("mode") == "TIME_AWARE" and evaluation_status == "completed"
            else "not_evaluated"
        ),
        "lead_inventory": "evaluated",
        "progress_out_of_sequence": (
            "evaluated_zero_lag_all_relationship_types"
            if date_based
            else "evaluated_time_aware_ss_actual_start_only"
        ),
        "progress_actual_consistency": (
            "evaluated_date_based"
            if date_based
            else "evaluated_status_and_actual_start_presence_only"
        ),
        "constraint_references_and_duplicates": "evaluated",
        "data_date_actual_consistency": data_date_status,
        "activity_calendar_assignment_integrity": "evaluated",
        "wbs_registry_and_activity_assignment": wbs_coverage,
        "baseline_metadata_and_activity_references": baseline_coverage,
        "resource_assignment_referential_integrity": resource_coverage,
        "resource_cost_quantity_reconciliation": (
            "not_evaluated_financial_policy_and_period_reconciliation_required"
            if resource_coverage.startswith("evaluated")
            else resource_coverage
        ),
        "excessive_lag_threshold": "not_evaluated_policy_pack_required",
        "long_duration_threshold": "not_evaluated_policy_pack_required",
        "excessive_constraint_threshold": "not_evaluated_policy_pack_required",
        "import_interchange_loss": "not_evaluated_persisted_import_reconciliation_required",
    }
    incomplete = [key for key, status in coverage.items() if status.startswith("not_evaluated")]
    partial = (
        evaluation_status != "completed"
        or bool(incomplete)
        or wbs_coverage.startswith("partial")
        or baseline_coverage.startswith("partial")
        or resource_coverage.startswith("partial")
    )

    return {
        "engine": "ENG-06",
        "engine_version": _ENGINE_VERSION,
        "status": "partial" if partial else "completed",
        "evaluation_status": evaluation_status,
        "snapshot": {
            "snapshot_id": payload.get("snapshot_id"),
            "snapshot_hash": hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest(),
            "project_id": payload.get("project_id"),
            "project_revision": payload.get("project_revision"),
            "mode": payload.get("mode"),
        },
        "summary": {
            "finding_count": len(findings),
            "critical_count": severity_counts["critical"],
            "warning_count": severity_counts["warning"],
            "info_count": severity_counts["info"],
            "open_predecessor_count": open_predecessors,
            "open_successor_count": open_successors,
            "invalid_relationship_count": invalid_relationship_count,
            "lead_count": lead_count,
            "positive_lag_count": positive_lag_count,
            "actual_after_data_date_count": actual_after_data_date,
            "out_of_sequence_candidate_count": out_of_sequence_candidates,
            "progress_consistency_finding_count": progress_consistency_count,
            "duplicate_constraint_count": duplicate_constraint_count,
            "invalid_constraint_reference_count": invalid_constraint_reference_count,
            "wbs_node_count": wbs_node_count,
            "baseline_count": baseline_count,
            "baseline_activity_count": baseline_activity_count,
            "resource_assignment_count": resource_assignment_count,
            "resource_period_count": resource_period_count,
            "activity_constraint_counts": dict(sorted(constraint_count_by_activity.items())),
        },
        "quality_index": {
            "status": "not_calculated",
            "value": None,
            "reason": "VERSIONED_WEIGHTED_POLICY_PACK_REQUIRED",
            "score_components": [],
        },
        "findings": findings,
        "coverage": coverage,
        "not_evaluated": incomplete,
        "remediation": {
            "status": "not_proposed",
            "reason": "READ_ONLY_AUDIT_REQUIRES_APPROVED_REMEDIATION_WORKFLOW",
        },
    }


__all__ = ["build_schedule_quality_audit"]
