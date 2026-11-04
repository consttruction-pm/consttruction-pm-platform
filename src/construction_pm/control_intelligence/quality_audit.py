from __future__ import annotations

"""Deterministic, read-only first-pass schedule quality audit.

The audit consumes the same immutable canonical schedule snapshot as the
Shared Scheduling Core. It does not calculate dates, float, criticality, costs
or resource demand. Those values remain owned by the Shared Core.
"""

from collections import defaultdict
from datetime import date
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


def build_schedule_quality_audit(
    canonical_payload: str,
    *,
    core_diagnostics: Sequence[Mapping[str, object]] = (),
    evaluation_status: str = "completed",
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
            or isinstance(lag, bool)
            or not isinstance(lag, int)
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

        edge_key = (predecessor, successor, relationship_type, lag)
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

        if lag < 0:
            lead_count += 1
            add(
                "RELATIONSHIP_LEAD_PRESENT",
                "warning",
                "quality.finding.relationship_lead_present",
                object_type="relationship",
                related_ids=(predecessor, successor),
                evidence=evidence,
            )
        elif lag > 0:
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
    for constraint in constraints:
        activity_id = constraint.get("activity_id")
        if isinstance(activity_id, str) and activity_id:
            constraint_count_by_activity[activity_id] += 1

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

    data_date = _iso_date(schedule_options.get("data_date"))
    actual_after_data_date = 0
    if data_date is not None:
        for activity_id, activity in sorted(activity_rows.items()):
            for field_name in ("actual_start", "actual_finish"):
                actual_value = _iso_date(activity.get(field_name))
                if actual_value is not None and actual_value > data_date:
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

    out_of_sequence_candidates = 0
    for relationship in valid_edges:
        if relationship.get("type", "FS") != "FS" or relationship.get("lag", 0) != 0:
            continue
        predecessor = str(relationship["predecessor_id"])
        successor = str(relationship["successor_id"])
        predecessor_finish = _iso_date(activity_rows[predecessor].get("actual_finish"))
        successor_start = _iso_date(activity_rows[successor].get("actual_start"))
        if (
            predecessor_finish is not None
            and successor_start is not None
            and successor_start < predecessor_finish
        ):
            out_of_sequence_candidates += 1
            add(
                "OUT_OF_SEQUENCE_PROGRESS_CANDIDATE",
                "warning",
                "quality.finding.out_of_sequence_progress_candidate",
                object_type="relationship",
                related_ids=(predecessor, successor),
                evidence={
                    "predecessor_actual_finish": predecessor_finish.isoformat(),
                    "successor_actual_start": successor_start.isoformat(),
                    "configured_oos_mode": schedule_options.get(
                        "out_of_sequence_schedule_type"
                    ),
                    "rule_scope": "FS_ZERO_LAG_ONLY",
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
        "evaluated" if data_date is not None else "not_evaluated_no_data_date"
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
        "excessive_lag_threshold": "not_evaluated_policy_pack_required",
        "long_duration_threshold": "not_evaluated_policy_pack_required",
        "excessive_constraint_threshold": "not_evaluated_policy_pack_required",
        "progress_out_of_sequence": "evaluated_fs_zero_lag_only",
        "data_date_actual_consistency": data_date_status,
        "activity_calendar_assignment_integrity": "evaluated",
        "baseline_integrity": "not_evaluated_baseline_snapshot_required",
        "wbs_and_code_completeness": "not_evaluated_authoritative_registry_required",
        "resource_cost_quantity_reconciliation": "not_evaluated_authoritative_resource_cost_inputs_required",
        "import_interchange_loss": "not_evaluated_import_reconciliation_required",
    }
    incomplete = [key for key, status in coverage.items() if status.startswith("not_evaluated")]
    partial = evaluation_status != "completed" or bool(incomplete)

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
