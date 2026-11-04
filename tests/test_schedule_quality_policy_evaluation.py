from __future__ import annotations

import json

from construction_pm.control_intelligence.quality_audit import build_schedule_quality_audit


def policy_pack() -> dict[str, object]:
    return {
        "policy_id": "schedule-quality",
        "version": "1.0.0",
        "name": "Approved schedule thresholds",
        "scoring_method": "weighted_pass_rate.v1",
        "approved_by": "admin-1",
        "approved_at": "2026-11-04T15:30:00+00:00",
        "thresholds": {
            "positive_lag": {
                "date_based_max_working_days": 5,
                "time_aware_max": {"working-day": "5", "working-hour": "40"},
                "severity": "warning",
            },
            "activity_duration": {
                "date_based_max_working_days": "6",
                "time_aware_max": {"working-day": "6", "working-hour": "48"},
                "severity": "critical",
            },
            "constraints_per_activity": {"maximum": 2, "severity": "warning"},
        },
        "weights": {
            "positive_lag": "0.50",
            "activity_duration": "0.30",
            "constraints_per_activity": "0.20",
        },
    }


def payload(*, mode: str = "DATE_BASED") -> str:
    if mode == "DATE_BASED":
        activities = [
            {"id": "A", "duration": 10, "duration_unit": "working-day", "activity_type": "Task Dependent"},
            {"id": "B", "duration": 5, "duration_unit": "working-day", "activity_type": "Task Dependent"},
            {"id": "C", "duration": 10, "duration_unit": "working-day", "activity_type": "Task Dependent"},
            {"id": "D", "duration": 3, "duration_unit": "working-day", "activity_type": "Task Dependent"},
        ]
        relationships = [
            {"predecessor_id": "A", "successor_id": "B", "type": "FS", "lag": 8},
            {"predecessor_id": "B", "successor_id": "C", "type": "FS", "lag": 2},
            {"predecessor_id": "C", "successor_id": "D", "type": "FS", "lag": 3},
            {"predecessor_id": "D", "successor_id": "A", "type": "SS", "lag": 1},
        ]
    else:
        activities = [
            {"id": "A", "duration": {"value": "60", "unit": "working-hour"}, "activity_type": "Task Dependent"},
            {"id": "B", "duration": {"value": "24", "unit": "working-hour"}, "activity_type": "Task Dependent"},
        ]
        relationships = [
            {"predecessor_id": "A", "successor_id": "B", "type": "FS", "lag": {"value": "50", "unit": "working-hour"}},
            {"predecessor_id": "B", "successor_id": "A", "type": "SS", "lag": {"value": "10", "unit": "working-hour"}},
        ]
    constraints = [
        {"activity_id": "B", "type": "Start On", "date": "2026-11-01"},
        {"activity_id": "B", "type": "Finish On", "date": "2026-11-02"},
        {"activity_id": "B", "type": "Must Finish By", "date": "2026-11-03"},
    ] if mode == "DATE_BASED" else []
    return json.dumps({
        "snapshot_id": "snapshot-policy",
        "tenant_id": "tenant-1",
        "project_id": "project-1",
        "project_revision": 9,
        "mode": mode,
        "activities": activities,
        "relationships": relationships,
        "constraints": constraints,
        "activity_calendar_assignments": [],
        "schedule_options": {},
    }, sort_keys=True, separators=(",", ":"))


def test_approved_policy_emits_three_threshold_findings_and_weighted_score() -> None:
    report = build_schedule_quality_audit(
        payload(),
        audit_context={
            "quality_policy_repository_configured": True,
            "approved_quality_policy_pack": policy_pack(),
        },
    )
    rules = [item["rule_id"] for item in report["findings"]]
    assert "EXCESSIVE_POSITIVE_LAG" in rules
    assert rules.count("LONG_ACTIVITY_DURATION") == 2
    assert "EXCESSIVE_CONSTRAINTS_PER_ACTIVITY" in rules
    assert report["quality_index"]["status"] == "calculated"
    assert report["quality_index"]["value"] == 67.5
    assert report["quality_index"]["policy"]["version"] == "1.0.0"
    assert report["coverage"]["excessive_lag_threshold"] == "evaluated_by_approved_policy_pack"
    assert report["coverage"]["long_duration_threshold"] == "evaluated_by_approved_policy_pack"
    assert report["coverage"]["excessive_constraint_threshold"] == "evaluated_by_approved_policy_pack"


def test_time_aware_policy_compares_lag_and_duration_only_in_matching_units() -> None:
    report = build_schedule_quality_audit(
        payload(mode="TIME_AWARE"),
        audit_context={
            "quality_policy_repository_configured": True,
            "approved_quality_policy_pack": policy_pack(),
        },
    )
    rules = [item for item in report["findings"] if item["rule_id"] in {
        "EXCESSIVE_POSITIVE_LAG", "LONG_ACTIVITY_DURATION"
    }]
    assert {item["rule_id"] for item in rules} == {
        "EXCESSIVE_POSITIVE_LAG", "LONG_ACTIVITY_DURATION"
    }
    assert report["quality_index"]["status"] == "calculated"
    lag = next(item for item in rules if item["rule_id"] == "EXCESSIVE_POSITIVE_LAG")
    assert lag["evidence"]["unit"] == "working-hour"
    duration = next(item for item in rules if item["rule_id"] == "LONG_ACTIVITY_DURATION")
    assert duration["evidence"]["unit"] == "working-hour"


def test_unapproved_or_unconfigured_policy_never_fabricates_a_score() -> None:
    unapproved = dict(policy_pack())
    unapproved["approved_by"] = None
    unapproved["approved_at"] = None
    report = build_schedule_quality_audit(
        payload(),
        audit_context={
            "quality_policy_repository_configured": True,
            "approved_quality_policy_pack": unapproved,
        },
    )
    assert report["quality_index"]["status"] == "not_calculated"
    assert report["quality_index"]["value"] is None
    assert report["quality_index"]["reason"] == "APPROVED_POLICY_PACK_INVALID"

    missing = build_schedule_quality_audit(payload())
    assert missing["quality_index"]["status"] == "not_calculated"
    assert missing["quality_index"]["reason"] == "APPROVED_POLICY_PACK_REQUIRED"


def test_positive_lag_score_excludes_zero_lag_and_negative_lead_observations() -> None:
    source = json.loads(payload())
    source["relationships"] = [
        {"predecessor_id": "A", "successor_id": "B", "type": "FS", "lag": 1},
        {"predecessor_id": "B", "successor_id": "C", "type": "FS", "lag": 0},
        {"predecessor_id": "C", "successor_id": "D", "type": "FS", "lag": -2},
    ]
    report = build_schedule_quality_audit(
        json.dumps(source, sort_keys=True, separators=(",", ":")),
        audit_context={
            "quality_policy_repository_configured": True,
            "approved_quality_policy_pack": policy_pack(),
        },
    )
    component = next(
        item for item in report["quality_index"]["score_components"]
        if item["rule"] == "positive_lag"
    )
    assert component["eligible_count"] == 1
    assert component["passed_count"] == 1
    assert component["failed_count"] == 0
