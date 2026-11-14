from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from construction_pm.scheduling.activity import Activity, ActivityType
from construction_pm.scheduling.constraints import ActivityConstraint, ConstraintType
from construction_pm.scheduling.relationships import Relationship
from construction_pm.scheduling.schedule_checks import (
    SCHEDULE_CHECK_RULES,
    ScheduleCheckRuleId,
    build_schedule_check_payload,
    evaluate_schedule_checks,
)


def _source(*activities, relationships=(), constraints=()):
    return SimpleNamespace(
        activities=tuple(activities),
        relationships=tuple(relationships),
        constraints=tuple(constraints),
    )


def test_open_start_and_finish_exclude_derived_activity_types():
    source = _source(
        Activity("A", 1),
        Activity("B", 1),
        Activity("C", 1),
        Activity("D", 1, activity_type=ActivityType.WBS_SUMMARY),
        Activity("E", 1, activity_type=ActivityType.LEVEL_OF_EFFORT),
        relationships=(
            Relationship("A", "B"),
            Relationship("A", "C"),
            Relationship("C", "B"),
        ),
    )

    findings = evaluate_schedule_checks(source)

    assert [item.rule_id for item in findings] == [
        ScheduleCheckRuleId.OPEN_START,
        ScheduleCheckRuleId.OPEN_FINISH,
    ]
    assert [item.activity_id for item in findings] == ["A", "B"]
    assert findings[0].severity.value == "WARNING"
    assert findings[0].details == {"predecessor_count": 0}
    assert findings[1].details == {"successor_count": 0}


def test_constraints_are_classified_and_mandatory_is_a_warning():
    source = _source(
        Activity("A", 1),
        Activity("B", 1),
        relationships=(Relationship("A", "B"),),
        constraints=(
            ActivityConstraint("A", ConstraintType.MANDATORY_FINISH, date(2026, 10, 30)),
            ActivityConstraint("B", ConstraintType.START_NO_EARLIER_THAN, date(2026, 10, 20)),
        ),
    )

    findings = evaluate_schedule_checks(source)
    by_rule = {item.rule_id: item for item in findings}

    assert by_rule[ScheduleCheckRuleId.MANDATORY_CONSTRAINT].severity.value == "WARNING"
    assert by_rule[ScheduleCheckRuleId.MANDATORY_CONSTRAINT].activity_id == "A"
    assert by_rule[ScheduleCheckRuleId.MANDATORY_CONSTRAINT].details == {
        "constraint_date": "2026-10-30",
        "constraint_type": "MANDATORY_FINISH",
        "mandatory": True,
    }
    assert by_rule[ScheduleCheckRuleId.ACTIVITY_CONSTRAINT].severity.value == "INFO"
    assert by_rule[ScheduleCheckRuleId.ACTIVITY_CONSTRAINT].activity_id == "B"
    assert by_rule[ScheduleCheckRuleId.ACTIVITY_CONSTRAINT].details["mandatory"] is False


def test_negative_lag_and_negative_float_are_reported_from_the_result():
    source = _source(
        Activity("A", 1),
        Activity("B", 1),
        relationships=(Relationship("A", "B", lag=-2),),
    )
    date_result = SimpleNamespace(
        floats={
            "A": SimpleNamespace(total_float=-1),
            "B": SimpleNamespace(total_float=3),
        }
    )

    findings = evaluate_schedule_checks(source, date_result=date_result)

    lag = next(item for item in findings if item.rule_id is ScheduleCheckRuleId.NEGATIVE_LAG)
    assert lag.severity.value == "INFO"
    assert lag.relationship_id == "A->B:FS"
    assert lag.activity_id == "B"
    assert lag.details["lag"] == "-2"
    negative_float = next(
        item for item in findings if item.rule_id is ScheduleCheckRuleId.NEGATIVE_FLOAT
    )
    assert negative_float.activity_id == "A"
    assert negative_float.severity.value == "WARNING"
    assert negative_float.details == {"total_float": "-1"}


def test_time_aware_negative_float_is_reported():
    from decimal import Decimal

    source = _source(
        Activity("A", 1),
        Activity("B", 1),
        relationships=(Relationship("A", "B"),),
    )
    time_result = SimpleNamespace(
        floats={
            "A": SimpleNamespace(total_float_value=Decimal("-0.5")),
            "B": SimpleNamespace(total_float_value=Decimal("2")),
        }
    )

    findings = evaluate_schedule_checks(source, time_result=time_result)

    assert [item.activity_id for item in findings if item.rule_id is ScheduleCheckRuleId.NEGATIVE_FLOAT] == ["A"]


def test_payload_lists_zero_count_rules_and_consistent_counts():
    source = _source(
        Activity("A", 1),
        relationships=(),
    )

    findings = evaluate_schedule_checks(source)
    payload = build_schedule_check_payload(
        findings,
        scope={"tenant_id": "T", "project_id": "P", "project_revision": 4},
        snapshot_id="S-1",
        snapshot_hash="a" * 64,
        calculation_run_identity="b" * 64,
    )

    assert payload["contract_version"] == "p6-schedule-check.v1"
    assert payload["kind"] == "schedule_check"
    assert payload["scope"] == {"tenant_id": "T", "project_id": "P", "project_revision": 4}
    assert payload["counts"] == {"total": 2, "ERROR": 0, "WARNING": 2, "INFO": 0}
    assert [rule["rule_id"] for rule in payload["rules"]] == [
        rule.rule_id.value for rule in SCHEDULE_CHECK_RULES
    ]
    counts = {rule["rule_id"]: rule["count"] for rule in payload["rules"]}
    assert counts["OPEN_START"] == 1
    assert counts["OPEN_FINISH"] == 1
    assert counts["NEGATIVE_FLOAT"] == 0
    assert counts["NEGATIVE_LAG"] == 0
    assert sum(counts.values()) == payload["counts"]["total"]


def test_empty_input_is_stable():
    findings = evaluate_schedule_checks(_source())
    assert findings == ()
    payload = build_schedule_check_payload(
        findings,
        scope={"tenant_id": "T", "project_id": "P", "project_revision": 1},
        snapshot_id="S-0",
        snapshot_hash="c" * 64,
        calculation_run_identity="d" * 64,
    )
    assert payload["counts"]["total"] == 0
    assert all(rule["count"] == 0 for rule in payload["rules"])
    assert payload["findings"] == []
